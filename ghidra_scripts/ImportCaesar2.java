// Import Caesar II debug symbols and set up the binary for analysis.
// Single-step script: reads symbols.json, disassembles code, imports symbols,
// sets calling conventions, applies line number comments, discovers hidden
// functions, organizes code into a Program Tree by source file, and applies
// known function signatures from decompiled source files.
//
// Run: uv run c2 export data/PS.EXE  (generates data/out/symbols.json first)
//
// The Program Tree folder mapping is read from config/program_tree.jsonc.
// Edit that file to customize how source files are grouped into folders.
// The .jsonc format supports // comments (parsed via Gson lenient mode).
//
// @category Caesar2
// @description All-in-one Caesar II setup: disassemble, import symbols, set
//   calling conventions, apply line numbers, discover hidden functions,
//   build Program Tree from source file mapping, apply decompiled signatures.

import ghidra.app.script.GhidraScript;
import ghidra.app.util.cparser.C.CParserUtils;
import ghidra.program.disassemble.Disassembler;
import ghidra.program.model.address.*;
import ghidra.program.model.symbol.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.data.*;
import ghidra.program.model.mem.*;

import java.io.*;
import java.nio.file.*;
import java.util.*;

import com.google.gson.*;
import com.google.gson.annotations.SerializedName;
import com.google.gson.stream.JsonReader;

public class ImportCaesar2 extends GhidraScript {

    // Data classes for symbols.json

    static class SymbolsJson {
        MemoryMap memory_map;
        List<Symbol> symbols;
        List<LineEntry> line_numbers;
        List<SourceFile> source_files;
    }

    static class MemoryMap {
        List<MemObject> objects;
        EntryPoint entry_point;
    }

    static class MemObject {
        String type;
        long base_address_int;
        long virtual_size;
    }

    static class EntryPoint {
        Long address_int;
    }

    static class Symbol {
        String name;
        boolean is_code;
        boolean is_data;
        String calling_convention;
        Long address;
    }

    static class LineEntry {
        String file;
        Integer line;
        Long address;
    }

    static class SourceFile {
        String file;
        String full_path;
        String source;
        Long min_address;
        Long max_address;
    }

    // Data classes for program_tree.jsonc

    static class TreeConfig {
        Sections sections;
        SourceTree source_tree;
    }

    static class Sections {
        String folder;
        List<SectionEntry> entries;
    }

    static class SectionEntry {
        String name;
        String start;
        String end;
    }

    static class SourceTree {
        String tree_name;
        String default_folder;
        List<FolderDef> folders;
    }

    static class FolderDef {
        String folder;
        List<String> match;
    }

    // Script logic

    // Cache for resolved calling convention names (source name → Ghidra name)
    private Map<String, String> conventionCache = new HashMap<>();

    @Override
    public AnalysisMode getScriptAnalysisMode() {
        // Suspend auto-analysis while the script runs so we can trigger it
        // explicitly at the right point (after Steps 1-5) and then fix up
        // what analysis got wrong in Step 6.
        return AnalysisMode.SUSPENDED;
    }

    @Override
    public void run() throws Exception {
        // Find symbols.json
        String jsonPath = findSymbolsJson();
        if (jsonPath == null) {
            popup("Could not find symbols.json.\n" +
                  "Run: uv run python -m caesar2 disasm/PS.EXE");
            return;
        }

        println("=== Caesar II Import ===");
        println("Reading from: " + jsonPath);

        // Parse symbols.json with Gson
        Gson gson = new Gson();
        SymbolsJson data;
        try (FileReader reader = new FileReader(jsonPath)) {
            data = gson.fromJson(reader, SymbolsJson.class);
        }

        MemoryMap memoryMap = data.memory_map;
        List<Symbol> symbols = data.symbols != null ? data.symbols : Collections.emptyList();
        List<LineEntry> lineNumbers = data.line_numbers != null ? data.line_numbers : Collections.emptyList();
        List<SourceFile> sourceFiles = data.source_files != null ? data.source_files : Collections.emptyList();
        println("Symbols: " + symbols.size() + ", Line entries: " + lineNumbers.size());

        // Find code and data objects
        List<MemObject> objects = memoryMap.objects != null ? memoryMap.objects : Collections.emptyList();
        EntryPoint entryPoint = memoryMap.entry_point;

        AddressSpace space = currentProgram.getAddressFactory().getDefaultAddressSpace();
        FunctionManager funcMgr = currentProgram.getFunctionManager();
        SymbolTable symTable = currentProgram.getSymbolTable();
        Listing listing = currentProgram.getListing();
        Memory memory = currentProgram.getMemory();

        // Create a synchronous disassembler — used throughout instead of
        // GhidraScript.disassemble() which is async (schedules work after
        // the script exits, so subsequent steps would see stale state).
        Disassembler disasm = Disassembler.getDisassembler(currentProgram, monitor, null);

        MemObject codeObj = null;
        MemObject dataObj = null;
        for (MemObject obj : objects) {
            if ("code".equals(obj.type)) codeObj = obj;
            else if ("data".equals(obj.type)) dataObj = obj;
        }

        // Step 1: Ensure code is disassembled
        // Ghidra's auto-analysis starts from the entry point and follows
        // control flow, but typically only covers ~23% of the code region.
        // We sweep through to fill gaps (functions reached via indirect
        // calls, function pointers, jump tables, etc.)
        println("\n--- Step 1: Disassembly sweep ---");
        int sweepCount = 0;

        if (codeObj != null) {
            long codeBase = codeObj.base_address_int;
            long codeSize = codeObj.virtual_size;
            println(String.format("Code object: 0x%X - 0x%X (%,d bytes)",
                codeBase, codeBase + codeSize - 1, codeSize));

            // Disassemble from code start (main is typically here)
            Address codeStart = space.getAddress(codeBase);
            disasm.disassemble(codeStart, null);

            // Disassemble from entry point
            if (entryPoint != null && entryPoint.address_int != null) {
                disasm.disassemble(space.getAddress(entryPoint.address_int), null);
            }

            // Sweep through code looking for undisassembled regions
            long stride = 0x100;
            for (long off = 0; off < codeSize; off += stride) {
                Address addr = space.getAddress(codeBase + off);
                if (getInstructionAt(addr) == null && getDataAt(addr) == null) {
                    disasm.disassemble(addr, null);
                    sweepCount++;
                }
            }
        }
        println("Disassembly sweep: " + sweepCount + " additional points triggered");

        // Step 2: Import symbols
        // Names are pre-demangled by the Python export (caesar2 package):
        //   Code: trailing "_" removed (TS_CODE_MANGLE "*_")
        //   Data: leading "_" removed (TS_DATA_MANGLE "_*")
        // See: open-watcom-v2/bld/comp_cfg/h/langenv.h
        println("\n--- Step 2: Importing symbols ---");
        int functionsRenamed = 0;
        int functionsCreated = 0;
        int labelsCreated = 0;
        int conventionsSet = 0;
        int conventionErrors = 0;
        int skipped = 0;
        int errors = 0;

        for (Symbol sym : symbols) {
            if (sym.address == null) {
                skipped++;
                continue;
            }

            Address addr = space.getAddress(sym.address);

            if (memory.getBlock(addr) == null) {
                skipped++;
                continue;
            }

            try {
                if (sym.is_code) {
                    // Try to find existing function at this address
                    Function func = funcMgr.getFunctionAt(addr);
                    if (func != null) {
                        String oldName = func.getName();
                        if (oldName.startsWith("FUN_") || oldName.equals("_entry")) {
                            func.setName(sym.name, SourceType.IMPORTED);
                            functionsRenamed++;
                        } else if (!oldName.equals(sym.name)) {
                            symTable.createLabel(addr, sym.name, SourceType.IMPORTED);
                            labelsCreated++;
                        }
                    } else {
                        // No function exists — create one
                        try {
                            disasm.disassemble(addr, null);
                            createFunction(addr, sym.name);
                            func = funcMgr.getFunctionAt(addr);
                            functionsCreated++;
                        } catch (Exception e) {
                            symTable.createLabel(addr, sym.name, SourceType.IMPORTED);
                            labelsCreated++;
                        }
                    }

                    // Set calling convention if available
                    if (func == null) {
                        func = funcMgr.getFunctionAt(addr);
                    }
                    if (func != null && sym.calling_convention != null) {
                        String ghidraConv = resolveCallingConvention(
                            sym.calling_convention, funcMgr);
                        if (ghidraConv != null) {
                            try {
                                func.setCallingConvention(ghidraConv);
                                conventionsSet++;
                            } catch (Exception e) {
                                if (conventionErrors == 0) {
                                    println("  Warning: convention '" + ghidraConv
                                        + "' failed: " + e.getMessage());
                                }
                                conventionErrors++;
                            }
                        }
                    }
                } else {
                    // Data or unknown — create label
                    symTable.createLabel(addr, sym.name, SourceType.IMPORTED);
                    labelsCreated++;
                }
            } catch (Exception e) {
                println(String.format("  Error processing %s at 0x%08X: %s",
                    sym.name, sym.address, e.getMessage()));
                errors++;
            }
        }

        println("Functions renamed:  " + functionsRenamed);
        println("Functions created:  " + functionsCreated);
        println("Labels created:     " + labelsCreated);
        println("Conventions set:    " + conventionsSet);
        println("Skipped:            " + skipped);
        println("Errors:             " + errors);

        // Step 3: Import line numbers
        println("\n--- Step 3: Importing line numbers ---");
        int linesApplied = 0;
        int linesSkipped = 0;

        for (LineEntry line : lineNumbers) {
            if (line.address == null) {
                linesSkipped++;
                continue;
            }

            Address addr = space.getAddress(line.address);
            if (memory.getBlock(addr) == null) {
                linesSkipped++;
                continue;
            }

            if (line.file == null || line.line == null) {
                linesSkipped++;
                continue;
            }

            String comment = line.file + ":" + line.line;
            listing.setComment(addr, CommentType.EOL, comment);
            linesApplied++;
        }

        println("Line comments applied: " + linesApplied);
        println("Line comments skipped: " + linesSkipped);

        // Step 4: Discover hidden functions (gaps only)
        // PS.EXE ships full Watcom -d1 debug info: 2261 code symbols name
        // EVERY function, and they cover 99.99% of the code object
        // (508325 / 508368 bytes; the only holes are 3 bytes of ___begtext
        // padding before the first symbol and 39 bytes after the last).
        //
        // Hidden-function discovery therefore runs ONLY over address ranges
        // that no debug symbol claims.  Inside a debug-covered range it is
        // not merely useless, it is destructive: the WatcomDebugAnalyzer
        // seeds each debug function with a 1-byte placeholder body (grown
        // later by flow analysis), so a function that ends in a tail-call JMP
        // or is reached only indirectly stays a 1-byte stub; its interior
        // then looks "outside any function" and every internal branch target
        // after a RET/JMP would be carved into a spurious FUN_ fragment.
        // Left unconstrained the old pass produced 4602 such fragments
        // shredding 1134 real functions (`main` alone split into 12 pieces).
        // The debug-symbol spans are authoritative; Step 5.5 re-imposes them.
        println("\n--- Step 4: Discovering hidden functions (gaps only) ---");

        // Sorted unique code-symbol offsets = authoritative function starts.
        TreeSet<Long> dbgAddrs = new TreeSet<>();
        for (Symbol sym : symbols) {
            if (sym.is_code && sym.address != null) {
                Address a = space.getAddress(sym.address);
                if (memory.getBlock(a) != null) dbgAddrs.add(sym.address);
            }
        }
        long codeEndExcl = (codeObj != null)
            ? codeObj.base_address_int + codeObj.virtual_size : 0L;

        int postTermCreated = 0;
        int fptrCreated = 0;
        int discoveryFailed = 0;
        int coveredSkipped = 0;

        if (codeObj != null) {
            long codeBase = codeObj.base_address_int;
            long codeSize = codeObj.virtual_size;
            Address codeStart = space.getAddress(codeBase);

            // 4a: Post-terminator referenced code — only outside debug spans.
            InstructionIterator scanIter = listing.getInstructions(codeStart, true);
            boolean prevWasTerminator = false;
            while (scanIter.hasNext()) {
                Instruction instr = scanIter.next();
                long instrAddr = instr.getAddress().getOffset();
                if (instrAddr > codeBase + codeSize) break;

                if (prevWasTerminator && funcMgr.getFunctionAt(instr.getAddress()) == null) {
                    if (isDebugCovered(instrAddr, dbgAddrs, codeEndExcl)) {
                        coveredSkipped++;
                    } else {
                        Reference[] refs = getReferencesTo(instr.getAddress());
                        if (refs.length > 0) {
                            try {
                                createFunction(instr.getAddress(), null);
                                postTermCreated++;
                            } catch (Exception e) {
                                discoveryFailed++;
                            }
                        }
                    }
                }

                String mnemonic = instr.getMnemonicString();
                prevWasTerminator = "RET".equals(mnemonic) || "RETN".equals(mnemonic) ||
                    "RETF".equals(mnemonic) || "JMP".equals(mnemonic) ||
                    "IRET".equals(mnemonic) || "IRETD".equals(mnemonic) ||
                    "HLT".equals(mnemonic) || "INT3".equals(mnemonic);
            }

            // 4b: Function pointers in data — only targets outside debug spans.
            if (dataObj != null) {
                long dataBase = dataObj.base_address_int;
                long dataSize = dataObj.virtual_size;

                for (long off = 0; off < dataSize - 3; off += 4) {
                    Address dataAddr = space.getAddress(dataBase + off);
                    try {
                        int val = memory.getInt(dataAddr);
                        long ptrVal = Integer.toUnsignedLong(val);

                        if (ptrVal >= codeBase && ptrVal < codeBase + codeSize) {
                            if (isDebugCovered(ptrVal, dbgAddrs, codeEndExcl)) {
                                coveredSkipped++;
                                continue;
                            }
                            Address targetAddr = space.getAddress(ptrVal);
                            if (getInstructionAt(targetAddr) != null &&
                                funcMgr.getFunctionAt(targetAddr) == null) {
                                try {
                                    createFunction(targetAddr, null);
                                    fptrCreated++;
                                } catch (Exception e) {
                                    discoveryFailed++;
                                }
                            }
                        }
                    } catch (Exception e) {
                        // Skip unreadable addresses
                    }
                }
            }
        }

        println("Post-terminator functions: " + postTermCreated);
        println("Data pointer functions:    " + fptrCreated);
        println("Skipped (debug-covered):   " + coveredSkipped);
        if (discoveryFailed > 0) {
            println("Discovery failures:        " + discoveryFailed);
        }

        // Step 5: Build Program Trees
        // Reads program_tree.jsonc (alongside symbols.json) to create:
        //   5a) Sections in the default "Program Tree" (broad subsystem ranges)
        //   5b) "Source Files" tree (individual source files with line numbers)
        // Uses Gson with lenient mode to support // comments in .jsonc.
        println("\n--- Step 5: Building Program Trees ---");

        // Look for config/program_tree.jsonc relative to repo root (two levels up from data/out/)
        File dataOutDir = new File(jsonPath).getParentFile();
        File repoRoot = dataOutDir != null ? dataOutDir.getParentFile() : null;
        if (repoRoot != null && repoRoot.getParentFile() != null) {
            // data/out/ -> data/ -> repo root
            repoRoot = repoRoot.getParentFile();
        }
        File treeConfigFile = repoRoot != null
            ? new File(repoRoot, "config/program_tree.jsonc")
            : new File(dataOutDir, "program_tree.jsonc");
        // Legacy fallback: same directory as symbols.json
        if (!treeConfigFile.exists()) {
            File legacy = new File(dataOutDir, "program_tree.jsonc");
            if (legacy.exists()) treeConfigFile = legacy;
        }
        if (!treeConfigFile.exists()) {
            println("No program_tree.jsonc found (checked config/ and data/out/)");
            println("  Skipping Program Trees (create config/program_tree.jsonc to enable)");
        } else {
            // Parse with Gson lenient mode (supports // and /* */ comments)
            TreeConfig treeConfig;
            try (JsonReader reader = new JsonReader(new FileReader(treeConfigFile))) {
                reader.setLenient(true);
                treeConfig = gson.fromJson(reader, TreeConfig.class);
            }
            println("Reading tree config: " + treeConfigFile.getPath());

            // 5a: Sections in default Program Tree
            int sectionCount = 0;
            int sectionErrors = 0;

            if (treeConfig.sections != null && treeConfig.sections.entries != null) {
                Sections sec = treeConfig.sections;
                String sectionsFolderName = sec.folder != null ? sec.folder : "Subsystems";

                ProgramModule defaultRoot = listing.getDefaultRootModule();
                String defaultTreeName = defaultRoot.getTreeName();

                ProgramModule sectionsFolder;
                try {
                    sectionsFolder = defaultRoot.createModule(sectionsFolderName);
                } catch (ghidra.util.exception.DuplicateNameException e) {
                    sectionsFolder = listing.getModule(defaultTreeName, sectionsFolderName);
                }

                for (SectionEntry entry : sec.entries) {
                    if (entry.name == null || entry.start == null || entry.end == null) continue;

                    try {
                        long startAddr = Long.decode(entry.start);
                        long endAddr = Long.decode(entry.end);
                        Address start = space.getAddress(startAddr);
                        Address end = space.getAddress(endAddr);

                        ProgramFragment frag;
                        try {
                            frag = sectionsFolder.createFragment(entry.name);
                        } catch (ghidra.util.exception.DuplicateNameException e) {
                            frag = listing.getFragment(defaultTreeName, entry.name);
                        }
                        if (frag != null) {
                            frag.move(start, end);
                            sectionCount++;
                        }
                    } catch (Exception e) {
                        if (sectionErrors == 0) {
                            println("  Section error for '" + entry.name + "': " + e.getMessage());
                        }
                        sectionErrors++;
                    }
                }
                println("Default Program Tree: " + sectionCount + " sections in '"
                    + sectionsFolderName + "'");
                if (sectionErrors > 0) {
                    println("  Section errors: " + sectionErrors);
                }
            }

            // 5b: Source Files tree
            SourceTree srcTree = treeConfig.source_tree;
            if (srcTree == null) srcTree = new SourceTree();
            String treeName = srcTree.tree_name != null ? srcTree.tree_name : "Source Files";
            String defaultFolder = srcTree.default_folder != null ? srcTree.default_folder : "Other";
            List<FolderDef> folderDefs = srcTree.folders != null ? srcTree.folders : Collections.emptyList();

            // Build folder → patterns map
            List<String> folderNames = new ArrayList<>();
            List<List<String>> folderPatterns = new ArrayList<>();
            for (FolderDef fd : folderDefs) {
                if (fd.folder == null) continue;
                folderNames.add(fd.folder);
                folderPatterns.add(fd.match != null ? fd.match : Collections.emptyList());
            }

            int treeFragments = 0;
            int treeErrors = 0;

            if (!sourceFiles.isEmpty()) {
                ProgramModule rootModule = null;
                try {
                    rootModule = listing.createRootModule(treeName);
                } catch (ghidra.util.exception.DuplicateNameException e) {
                    rootModule = listing.getRootModule(treeName);
                }

                if (rootModule != null) {
                    // Move auto-created default fragments (.image, .object1, etc.)
                    // into a "Memory Blocks" folder to keep them out of the way.
                    ProgramModule memBlocksFolder = null;
                    try {
                        memBlocksFolder = rootModule.createModule("Memory Blocks");
                    } catch (ghidra.util.exception.DuplicateNameException e) {
                        memBlocksFolder = listing.getModule(treeName, "Memory Blocks");
                    }
                    if (memBlocksFolder != null) {
                        for (Group child : rootModule.getChildren()) {
                            if (child instanceof ProgramFragment) {
                                try {
                                    memBlocksFolder.add((ProgramFragment) child);
                                    rootModule.removeChild(child.getName());
                                } catch (Exception e) {
                                    // ignore — fragment may be shared
                                }
                            }
                        }
                    }

                    // Create folder modules
                    Map<String, ProgramModule> folderModules = new HashMap<>();
                    for (String fn : folderNames) {
                        try {
                            folderModules.put(fn, rootModule.createModule(fn));
                        } catch (ghidra.util.exception.DuplicateNameException e) {
                            folderModules.put(fn, listing.getModule(treeName, fn));
                        }
                    }
                    ProgramModule defaultModule;
                    try {
                        defaultModule = rootModule.createModule(defaultFolder);
                    } catch (ghidra.util.exception.DuplicateNameException e) {
                        defaultModule = listing.getModule(treeName, defaultFolder);
                    }

                    // Only include source files with line numbers
                    for (SourceFile sf : sourceFiles) {
                        if (!"lines".equals(sf.source)) continue;
                        if (sf.file == null || sf.min_address == null || sf.max_address == null) continue;

                        // Find matching folder
                        ProgramModule targetModule = defaultModule;
                        for (int i = 0; i < folderNames.size(); i++) {
                            for (String pattern : folderPatterns.get(i)) {
                                if (matchesPattern(sf.full_path, pattern) ||
                                    matchesPattern(sf.file, pattern)) {
                                    targetModule = folderModules.get(folderNames.get(i));
                                    break;
                                }
                            }
                            if (targetModule != defaultModule) break;
                        }

                        // Create fragment and move address range
                        try {
                            ProgramFragment frag;
                            try {
                                frag = targetModule.createFragment(sf.file);
                            } catch (ghidra.util.exception.DuplicateNameException e) {
                                frag = listing.getFragment(treeName, sf.file);
                            }
                            if (frag != null) {
                                Address start = space.getAddress(sf.min_address);
                                Address end = space.getAddress(sf.max_address);
                                frag.move(start, end);
                                treeFragments++;
                            }
                        } catch (Exception e) {
                            if (treeErrors == 0) {
                                println("  Tree error for " + sf.file + ": " + e.getMessage());
                            }
                            treeErrors++;
                        }
                    }

                    // Remove empty folders
                    List<String> usedFolders = new ArrayList<>();
                    for (String fn : folderNames) {
                        ProgramModule mod = folderModules.get(fn);
                        if (mod != null && mod.getNumChildren() == 0) {
                            try { rootModule.removeChild(fn); } catch (Exception e) { }
                        } else if (mod != null) {
                            usedFolders.add(fn);
                        }
                    }
                    if (defaultModule != null && defaultModule.getNumChildren() == 0) {
                        try { rootModule.removeChild(defaultFolder); } catch (Exception e) { }
                    } else {
                        usedFolders.add(defaultFolder);
                    }

                    println("Source Files tree: " + treeFragments + " fragments");
                    if (treeErrors > 0) {
                        println("  Tree errors: " + treeErrors);
                    }
                    println("  Folders: " + usedFolders);
                }
            }
        }

        // Trigger auto-analysis
        // Steps 1-5 are complete. Now run auto-analysis synchronously so that
        // CallFixupAnalyzer, FindNoReturnFunctionsAnalyzer, etc. all run to
        // completion before Step 6 fixes up what they got wrong.
        println("\n--- Running auto-analysis ---");
        analyzeAll(currentProgram);
        println("Auto-analysis complete.");

        // Step 5.5: Normalize function boundaries to debug spans
        // The debug symbols are authoritative: functions are laid out
        // contiguously, so every body is exactly [symbol, nextSymbol).
        // Auto-analysis and the WatcomDebugAnalyzer's 1-byte placeholder
        // bodies leave many debug functions as stubs (a tail-call JMP or an
        // indirect-only entry never grows) and Ghidra's own analyzers can
        // still carve a stub's interior into fragments.  Rebuild the truth:
        //   a) delete every non-debug function inside the debug-covered code
        //      range — those are spurious fragments of named functions;
        //   b) set each debug function's body to its contiguous span,
        //      creating the function if a prior absorption left only a label.
        println("\n--- Step 5.5: Normalizing function boundaries ---");
        int fragmentsDeleted = 0;
        int bodiesFixed = 0;
        int boundaryCreated = 0;
        int boundaryFailed = 0;

        if (codeObj != null && !dbgAddrs.isEmpty()) {
            long nCodeBase = codeObj.base_address_int;
            long nCodeEnd = nCodeBase + codeObj.virtual_size;   // exclusive

            // Pass 1: delete spurious (non-debug) functions that sit INSIDE a
            // debug span (i.e. fragments of a named function).  Functions in
            // a genuine gap (before the first symbol) are left alone.
            List<Address> frags = new ArrayList<>();
            FunctionIterator fIt = funcMgr.getFunctions(true);
            while (fIt.hasNext()) {
                Function f = fIt.next();
                long e = f.getEntryPoint().getOffset();
                if (!dbgAddrs.contains(e) && isDebugCovered(e, dbgAddrs, nCodeEnd)) {
                    frags.add(f.getEntryPoint());
                }
            }
            for (Address a : frags) {
                if (funcMgr.removeFunction(a)) fragmentsDeleted++;
            }

            // primary name / convention per address (first symbol, file order)
            Map<Long,String> primaryName = new HashMap<>();
            Map<Long,String> primaryConv = new HashMap<>();
            for (Symbol sym : symbols) {
                if (sym.is_code && sym.address != null && !primaryName.containsKey(sym.address)) {
                    primaryName.put(sym.address, sym.name);
                    primaryConv.put(sym.address, sym.calling_convention);
                }
            }

            // Pass 2: contiguous body per debug function.  Ascending order
            // guarantees an over-long predecessor is shrunk before we reach
            // the address it used to absorb, so no setBody overlaps.
            List<Long> ordered = new ArrayList<>(dbgAddrs);
            for (int i = 0; i < ordered.size(); i++) {
                long a = ordered.get(i);
                long end = (i + 1 < ordered.size()) ? ordered.get(i + 1) : nCodeEnd; // excl
                if (end <= a) continue;
                Address start = space.getAddress(a);
                Address lastAddr = space.getAddress(end - 1);
                AddressSet body = new AddressSet(start, lastAddr);

                // Clear the span of any OTHER function (a fragment that Pass 1
                // missed, or a neighbour Ghidra grew across the boundary) so
                // the body assignment below can never hit an overlap.  Code
                // after an early RET reached only by a jump is the common
                // culprit (e.g. go_16m_palette, clear_army, __MemAllocator).
                List<Address> overlap = new ArrayList<>();
                Iterator<Function> ov = funcMgr.getFunctionsOverlapping(body);
                while (ov.hasNext()) {
                    Function of = ov.next();
                    if (of.getEntryPoint().getOffset() != a) {
                        overlap.add(of.getEntryPoint());
                    }
                }
                for (Address k : overlap) {
                    if (funcMgr.removeFunction(k)) fragmentsDeleted++;
                }

                Function f = funcMgr.getFunctionAt(start);
                if (f == null) {
                    // Absorbed earlier (left as a label) — (re)create it.
                    try {
                        Function nf = funcMgr.createFunction(
                            primaryName.get(a), start, body, SourceType.IMPORTED);
                        boundaryCreated++;
                        String conv = primaryConv.get(a);
                        if (nf != null && conv != null) {
                            String gc = resolveCallingConvention(conv, funcMgr);
                            if (gc != null) {
                                try { nf.setCallingConvention(gc); } catch (Exception ex) { }
                            }
                        }
                    } catch (Exception e) {
                        boundaryFailed++;
                        println("  Boundary create failed @ " + start + ": " + e.getMessage());
                    }
                } else {
                    AddressSetView cur = f.getBody();
                    boolean ok = cur.getNumAddresses() == (end - a)
                        && cur.getMinAddress().getOffset() == a
                        && cur.getMaxAddress().getOffset() == end - 1;
                    if (!ok) {
                        try {
                            f.setBody(body);
                            bodiesFixed++;
                        } catch (Exception e) {
                            boundaryFailed++;
                            println("  Boundary setBody failed @ " + start + ": " + e.getMessage());
                        }
                    }
                }
            }
        }
        println("Fragments deleted:        " + fragmentsDeleted);
        println("Bodies normalized:        " + bodiesFixed);
        println("Boundary functions made:  " + boundaryCreated);
        if (boundaryFailed > 0) println("Boundary failures:        " + boundaryFailed);

        // Step 6: Fix noreturn functions that should return
        // Two Watcom patterns cause functions to be incorrectly marked noreturn:
        //
        // Pattern A — callfixup noreturn: __CHK/__STK have a callfixup set
        //   (watcom_stack_check) but Ghidra's CallFixupAnalyzer does not clear
        //   the noreturn flag. The disassembler checks hasNoReturn() first, so
        //   CALL_RETURN overrides are still applied at every call site even
        //   though the callfixup models fall-through. Fix: clear noreturn on
        //   every function that has the watcom_stack_check callfixup.
        //
        // Pattern B — shared epilogue: Watcom sometimes generates code where
        //   multiple functions share a single POP/RET epilogue block. A function
        //   that tail-jumps to the shared epilogue ends with JMP rather than RET,
        //   so Ghidra marks it noreturn. Fix: detect noreturn functions whose
        //   last instruction is JMP and clear the noreturn flag.
        //
        // After clearing noreturn, clear CALL_RETURN flow overrides at all call
        // sites and synchronously re-disassemble the fall-through bytes.
        println("\n--- Step 6: Fix noreturn functions that should return ---");
        int callfixupNoreturnFixed = 0;
        int sharedEpilogueFixed = 0;
        int callReturnOverridesCleared = 0;
        int fallThroughsRedisassembled = 0;

        AddressSet step6FallThroughs = new AddressSet();

        // Helper: clear CALL_RETURN overrides at all call sites of a function
        // and collect fall-through addresses for re-disassembly.
        // (Defined inline via iteration — Java scripts can't use lambdas easily.)

        FunctionIterator step6Iter = funcMgr.getFunctions(true);
        while (step6Iter.hasNext()) {
            Function func = step6Iter.next();
            boolean shouldFix = false;

            // Pattern A: has watcom_stack_check callfixup but still marked noreturn
            String fixup = func.getCallFixup();
            if ("watcom_stack_check".equals(fixup) && func.hasNoReturn()) {
                func.setNoReturn(false);
                callfixupNoreturnFixed++;
                println("  Cleared noreturn (callfixup): " + func.getName()
                    + " @ " + func.getEntryPoint());
                shouldFix = true;
            }

            // Pattern B: noreturn function whose last instruction is JMP
            if (!shouldFix && func.hasNoReturn()) {
                Instruction lastInstr = null;
                InstructionIterator instrIter = listing.getInstructions(func.getBody(), true);
                while (instrIter.hasNext()) {
                    lastInstr = instrIter.next();
                }
                if (lastInstr != null && lastInstr.getMnemonicString().startsWith("JMP")) {
                    func.setNoReturn(false);
                    sharedEpilogueFixed++;
                    println("  Cleared noreturn (shared epilogue): " + func.getName()
                        + " @ " + func.getEntryPoint()
                        + "  (last: JMP " + lastInstr.getDefaultOperandRepresentation(0) + ")");
                    shouldFix = true;
                }
            }

            if (!shouldFix) continue;

            // Clear CALL_RETURN overrides at all call sites and collect fall-throughs
            for (Reference ref : getReferencesTo(func.getEntryPoint())) {
                if (!ref.getReferenceType().isCall()) continue;
                Address callSite = ref.getFromAddress();
                Instruction callInstr = getInstructionAt(callSite);
                if (callInstr == null) continue;
                if (callInstr.getFlowOverride() != FlowOverride.CALL_RETURN) continue;
                callInstr.setFlowOverride(FlowOverride.NONE);
                callReturnOverridesCleared++;
                Address fallThrough = callSite.add(callInstr.getLength());
                if (getInstructionAt(fallThrough) == null) {
                    step6FallThroughs.addRange(fallThrough, fallThrough);
                }
            }
        }

        if (!step6FallThroughs.isEmpty()) {
            AddressSet disassembled = disasm.disassemble(step6FallThroughs, null, true);
            fallThroughsRedisassembled = (int) disassembled.getNumAddressRanges();
        }

        println("Callfixup noreturn cleared:      " + callfixupNoreturnFixed);
        println("Shared-epilogue noreturn cleared: " + sharedEpilogueFixed);
        println("CALL_RETURN overrides cleared:   " + callReturnOverridesCleared);
        println("Fall-throughs re-disassembled:   " + fallThroughsRedisassembled);

        // Step 7: Apply known function signatures from decompiled sources
        // Signatures derived from decomp/src/formulae.c.  Re-applying them
        // here ensures they survive a fresh import and improve decompilation
        // quality for callers of these functions in other source files.
        println("\n--- Step 7: Applying decompiled function signatures ---");

        DataType intT  = IntegerDataType.dataType;
        DataType voidT = VoidDataType.dataType;

        // Label aliases discovered during decompilation
        setLabel(space, 0x9d024L, "skill_level");
        setLabel(space, 0x9d025L, "peaceful_mode");

        // formulae.c — 43 functions
        setSig(funcMgr, "check_game_over", voidT, new String[]{});
        setSig(funcMgr, "check_for_promotion", voidT, new String[]{});
        setSig(funcMgr, "adjust_peace_criteria", voidT, new String[]{});
        setSig(funcMgr, "adjust_culture_criteria", voidT, new String[]{});
        setSig(funcMgr, "adjust_proserity_criteria", voidT, new String[]{});
        setSig(funcMgr, "adjust_empire_criteria", voidT, new String[]{});
        setSig(funcMgr, "city_pop_limit_10_to_1", intT, new String[]{"value", "factor"});
        setSig(funcMgr, "want_promotion", intT, new String[]{"level"});
        setSig(funcMgr, "act_take_promotion", voidT, new String[]{});
        setSig(funcMgr, "act_review_in_10", voidT, new String[]{});
        setSig(funcMgr, "act_review_in_25", voidT, new String[]{});
        setSig(funcMgr, "assign_to_new_province", voidT, new String[]{});
        setSig(funcMgr, "do_promotion", voidT, new String[]{"level"});
        setSig(funcMgr, "make_emperor", voidT, new String[]{});
        setSig(funcMgr, "init_legion", voidT, new String[]{});
        setSig(funcMgr, "train_soldiers", voidT, new String[]{});
        setSig(funcMgr, "get_morale_and_readiness", voidT, new String[]{});
        setSig(funcMgr, "get_current_cohort_totals", voidT, new String[]{});
        setSig(funcMgr, "set_current_cohort_totals", voidT, new String[]{});
        setSig(funcMgr, "fill_cohort_centuries", voidT, new String[]{});
        setSig(funcMgr, "get_army_totals", voidT, new String[]{});
        setSig(funcMgr, "predict_army_totals", voidT, new String[]{});
        setSig(funcMgr, "init_slaves", voidT, new String[]{});
        setSig(funcMgr, "slave_welfare", voidT, new String[]{});
        setSig(funcMgr, "slave_costs", voidT, new String[]{});
        setSig(funcMgr, "slave_estimate", voidT, new String[]{});
        setSig(funcMgr, "adjust_slave_usage", voidT, new String[]{});
        setSig(funcMgr, "random_event", voidT, new String[]{});
        setSig(funcMgr, "pay_salary", voidT, new String[]{});
        setSig(funcMgr, "get_population_growth_factor", voidT, new String[]{});
        setSig(funcMgr, "get_industry_growth_factor", voidT, new String[]{});
        setSig(funcMgr, "get_insurrection_factor", voidT, new String[]{});
        setSig(funcMgr, "year_end_accounts", voidT, new String[]{});
        setSig(funcMgr, "collect_pop_tax", voidT, new String[]{});
        setSig(funcMgr, "collect_ind_tax", voidT, new String[]{});
        setSig(funcMgr, "get_estimates", voidT, new String[]{});
        setSig(funcMgr, "get_pop_tax_estimate", voidT, new String[]{});
        setSig(funcMgr, "get_ind_tax_estimate", voidT, new String[]{});
        setSig(funcMgr, "get_average_pop_tax", voidT, new String[]{});
        setSig(funcMgr, "get_average_ind_tax", voidT, new String[]{});
        setSig(funcMgr, "get_new_tribute", voidT, new String[]{});
        setSig(funcMgr, "init_tribute", voidT, new String[]{});
        setSig(funcMgr, "get_temple_tip", voidT, new String[]{"param_1"});

        // Step 8: Apply recovered types from decomp/include headers
        // Ghidra's C parser handles the reconstructed headers as-is — macros,
        // #includes and all.  Parsing c2_funcs.h pulls in c2_types.h ->
        // entities.h, so ONE parse yields every struct / enum / typedef AND a
        // FunctionDefinition per prototype.  We then (8b) apply each
        // function's signature with the __watcall convention, and (8c) type
        // every struct-valued global (array size taken from the data-segment
        // span, so the macro array dimensions never need evaluating here).
        // This supersedes the hand-written formulae.c signatures in Step 7.
        println("\n--- Step 8: Applying recovered types ---");
        DataTypeManager dtm = currentProgram.getDataTypeManager();

        File symJsonFile = new File(jsonPath);
        File incDir = null;
        if (symJsonFile.getParentFile() != null
                && symJsonFile.getParentFile().getParentFile() != null
                && symJsonFile.getParentFile().getParentFile().getParentFile() != null) {
            incDir = new File(symJsonFile.getParentFile().getParentFile()
                .getParentFile(), "decomp/include");
        }

        int sigsApplied = 0, sigErrors = 0;
        int globalsTyped = 0, globalTypeErrors = 0;

        if (incDir != null && new File(incDir, "c2_funcs.h").exists()) {
            // 8a: parse headers -> data types + FunctionDefinition per prototype
            try {
                CParserUtils.CParseResults pr = CParserUtils.parseHeaderFiles(
                    new DataTypeManager[]{},
                    new String[]{ new File(incDir, "c2_funcs.h").getAbsolutePath() },
                    new String[]{ incDir.getAbsolutePath() },
                    new String[]{}, dtm, monitor);
                println("  Header parse: successful=" + pr.successful());
            } catch (Exception e) {
                println("  Header parse FAILED: " + e.getMessage());
            }

            // Watcom 10.0a builds with PackAmount=1 (no implicit alignment
            // padding).  Ghidra's parser used the default C data organization,
            // which pads (e.g. dpmi_real_block int+short -> 8 not 6).  Force
            // 1-byte packing on every parsed composite so sizes AND field
            // offsets match the binary exactly.
            List<Composite> comps = new ArrayList<>();
            Iterator<DataType> allDt = dtm.getAllDataTypes();
            while (allDt.hasNext()) {
                DataType d = allDt.next();
                if (d instanceof Composite) comps.add((Composite) d);
            }
            int packed = 0;
            for (Composite c : comps) {
                try { c.setExplicitPackingValue(1); packed++; } catch (Exception e) { }
            }
            println("  Composites packed to 1 byte: " + packed);

            // 8b: apply function signatures (+ __watcall) wherever a
            //     FunctionDefinition of the same name was parsed.  (CParser
            //     nests them under an include-file category, so resolve by
            //     name rather than a fixed CategoryPath.)
            List<DataType> defCand = new ArrayList<>();
            for (Function f : funcMgr.getFunctions(true)) {
                defCand.clear();
                dtm.findDataTypes(f.getName(), defCand);
                FunctionDefinition fd = null;
                for (DataType d : defCand) {
                    if (d instanceof FunctionDefinition) { fd = (FunctionDefinition) d; break; }
                }
                if (fd == null) continue;
                try {
                    applyFuncDef(f, fd, "__watcall");
                    sigsApplied++;
                } catch (Exception e) {
                    sigErrors++;
                    if (sigErrors <= 5) {
                        println("  sig error " + f.getName() + ": " + e.getMessage());
                    }
                }
            }

            // 8c: type EVERY global from the header extern declarations —
            //     structs, scalars (int/char/short + signed/unsigned),
            //     pointers and arrays.  Array element counts come from the
            //     data-segment span, so macro dimensions (CITY_W*CITY_H, ...)
            //     never need evaluating; the outermost dim is span-derived and
            //     any inner dims must be plain integers.
            //     Grammar: extern <base> <ptrs> <name> <arrays> ;
            TreeSet<Long> dataAddrs = new TreeSet<>();
            long dataEndExcl = (dataObj != null)
                ? dataObj.base_address_int + dataObj.virtual_size : 0L;
            for (Symbol s : symbols) {
                if (s.is_data && s.address != null) dataAddrs.add(s.address);
            }
            java.util.regex.Pattern pat = java.util.regex.Pattern.compile(
                "^\\s*extern\\s+(.+?)\\s*(\\*+)?\\s*\\b(\\w+)\\s*((?:\\[[^\\]]*\\])*)\\s*;");
            for (String hdr : new String[]{"entities.h", "c2_types.h", "c2_data.h"}) {
                File hf = new File(incDir, hdr);
                if (!hf.exists()) continue;
                for (String line : java.nio.file.Files.readAllLines(hf.toPath())) {
                    java.util.regex.Matcher m = pat.matcher(line);
                    if (!m.find()) continue;
                    try {
                        if (typeGlobal(dtm, symTable, listing, dataAddrs, dataEndExcl,
                                m.group(1).trim(),
                                m.group(2) == null ? 0 : m.group(2).length(),
                                m.group(3), m.group(4))) {
                            globalsTyped++;
                        }
                    } catch (Exception e) {
                        globalTypeErrors++;
                    }
                }
            }
            // 8d: Miles AIL library signatures.  The AIL API is __cdecl
            //     (caller-pushed args, caller cleanup); the game name AIL_xxx
            //     maps to the linker symbol _AIL_xxx.  (Smacker's SmackXxx are
            //     __pascal, which the x86:LE:32:watcom cspec does not define,
            //     so they are left alone until the cspec gains __pascal.)
            int ailApplied = applyLibraryHeader(
                dtm, funcMgr, incDir, "ail.h", "__cdecl", true, false);
            println("AIL signatures applied:      " + ailApplied);
        } else {
            println("  decomp/include not found — skipping type application.");
        }
        println("Function signatures applied: " + sigsApplied);
        println("Globals typed:               " + globalsTyped);
        if (sigErrors > 0) println("Signature errors:            " + sigErrors);
        if (globalTypeErrors > 0) println("Global type errors:          " + globalTypeErrors);

        // Summary
        println("\n=== Import Complete ===");
        int totalFuncs = 0;
        FunctionIterator funcIter = funcMgr.getFunctions(true);
        while (funcIter.hasNext()) {
            funcIter.next();
            totalFuncs++;
        }
        println("Total functions in program: " + totalFuncs);
    }

    // Step 7 helpers

    private void setLabel(AddressSpace space, long offset, String name) throws Exception {
        Address addr = space.getAddress(offset);
        ghidra.program.model.symbol.Symbol existing = currentProgram.getSymbolTable().getPrimarySymbol(addr);
        if (existing != null && existing.getName().equals(name)) return;
        ghidra.program.model.symbol.Symbol lbl = currentProgram.getSymbolTable()
            .createLabel(addr, name, SourceType.USER_DEFINED);
        lbl.setPrimary();
        println("  label: " + name + " @ " + addr);
    }

    private void setSig(FunctionManager fm, String name, DataType ret, String[] pnames)
            throws Exception {
        Function f = null;
        for (Function fn : fm.getFunctions(true)) {
            if (fn.getName().equals(name)) { f = fn; break; }
        }
        if (f == null) { println("  setSig: not found: " + name); return; }
        List<Parameter> plist = new ArrayList<>();
        for (String pn : pnames) {
            plist.add(new ParameterImpl(pn, IntegerDataType.dataType, currentProgram));
        }
        f.updateFunction("__watcall", new ReturnParameterImpl(ret, currentProgram),
            plist, Function.FunctionUpdateType.DYNAMIC_STORAGE_FORMAL_PARAMS,
            true, SourceType.USER_DEFINED);
    }

    // Step 8 helpers

    /** Apply a parsed FunctionDefinition (return type + params) to a real
     *  function under the given calling convention (storage is recomputed
     *  for the formal params). */
    private void applyFuncDef(Function f, FunctionDefinition fd, String conv) throws Exception {
        DataType ret = fd.getReturnType();
        ParameterDefinition[] args = fd.getArguments();
        List<Parameter> plist = new ArrayList<>();
        for (ParameterDefinition pd : args) {
            String pn = pd.getName();
            if (pn != null && pn.isEmpty()) pn = null;
            plist.add(new ParameterImpl(pn, pd.getDataType(), currentProgram));
        }
        f.updateFunction(conv, new ReturnParameterImpl(ret, currentProgram),
            plist, Function.FunctionUpdateType.DYNAMIC_STORAGE_FORMAL_PARAMS,
            true, SourceType.IMPORTED);
        if (fd.hasVarArgs()) f.setVarArgs(true);
    }

    /** Parse a library header (stripping Watcom #pragma lines that Ghidra's C
     *  parser rejects) and apply each prototype's signature to its PS.EXE
     *  function under the given convention.  The linker name is the prototype
     *  name transformed: optional leading '_' and/or upper-casing. */
    private int applyLibraryHeader(DataTypeManager dtm, FunctionManager funcMgr,
            File incDir, String header, String conv,
            boolean addUnderscore, boolean upper) {
        int applied = 0;
        try {
            File hf = new File(incDir, header);
            if (!hf.exists()) return 0;
            StringBuilder sb = new StringBuilder();
            for (String ln : java.nio.file.Files.readAllLines(hf.toPath())) {
                if (ln.trim().startsWith("#pragma")) continue;
                sb.append(ln).append("\n");
            }
            File tmp = File.createTempFile("c2lib_", "_" + header);
            java.nio.file.Files.write(tmp.toPath(), sb.toString().getBytes());
            CParserUtils.parseHeaderFiles(new DataTypeManager[]{},
                new String[]{ tmp.getAbsolutePath() },
                new String[]{ incDir.getAbsolutePath() },
                new String[]{}, dtm, monitor);
            tmp.delete();

            java.util.regex.Matcher nm = java.util.regex.Pattern
                .compile("\\b(\\w+)\\s*\\([^;{]*\\)\\s*;").matcher(sb.toString());
            SymbolTable st = currentProgram.getSymbolTable();
            while (nm.find()) {
                String pn = nm.group(1);
                List<DataType> cand = new ArrayList<>();
                dtm.findDataTypes(pn, cand);
                FunctionDefinition fd = null;
                for (DataType d : cand) {
                    if (d instanceof FunctionDefinition) { fd = (FunctionDefinition) d; break; }
                }
                if (fd == null) continue;
                String gname = (upper ? pn.toUpperCase() : pn);
                if (addUnderscore) gname = "_" + gname;
                Function f = null;
                for (ghidra.program.model.symbol.Symbol s : st.getGlobalSymbols(gname)) {
                    Function ff = funcMgr.getFunctionAt(s.getAddress());
                    if (ff != null) { f = ff; break; }
                }
                if (f == null) continue;
                try { applyFuncDef(f, fd, conv); applied++; } catch (Exception e) { }
            }
        } catch (Exception e) {
            println("  library " + header + ": " + e.getMessage());
        }
        return applied;
    }

    /** Type any global from its extern declaration.  base + ptr count + name +
     *  array suffix are pre-split by the caller.  Array element counts come
     *  from the data-segment span (outermost dim); inner dims must be plain
     *  ints, so macro array dimensions never need evaluating. */
    private boolean typeGlobal(DataTypeManager dtm, SymbolTable symTable,
            Listing listing, TreeSet<Long> dataAddrs, long dataEndExcl,
            String baseSpec, int ptrCount, String varName, String arraySuffix)
            throws Exception {
        DataType t = resolveBaseType(dtm, baseSpec);
        if (t == null) return false;
        for (int i = 0; i < ptrCount; i++) t = new PointerDataType(t);

        List<ghidra.program.model.symbol.Symbol> syms =
            symTable.getGlobalSymbols(varName);
        if (syms.isEmpty()) return false;
        Address addr = syms.get(0).getAddress();

        List<String> dims = new ArrayList<>();
        if (arraySuffix != null && !arraySuffix.isEmpty()) {
            java.util.regex.Matcher dm = java.util.regex.Pattern
                .compile("\\[([^\\]]*)\\]").matcher(arraySuffix);
            while (dm.find()) dims.add(dm.group(1).trim());
        }
        // inner dims (all but outermost), right-to-left; plain ints only
        for (int i = dims.size() - 1; i >= 1; i--) {
            int n = -1;
            try { n = Integer.decode(dims.get(i)); } catch (Exception e) { }
            if (n <= 0) n = 1;
            if (t.getLength() <= 0) return false;
            t = new ArrayDataType(t, n, t.getLength());
        }
        // outermost dim from the data-segment span
        if (!dims.isEmpty()) {
            if (t.getLength() <= 0) return false;
            Long next = dataAddrs.higher(addr.getOffset());
            long end = (next != null) ? next : dataEndExcl;
            int count = (int) ((end - addr.getOffset()) / t.getLength());
            if (count < 1) count = 1;
            t = new ArrayDataType(t, count, t.getLength());
        }
        if (t.getLength() <= 0) return false;
        try {
            listing.clearCodeUnits(addr, addr.add(t.getLength() - 1), false);
        } catch (Exception e) {
            // best-effort
        }
        listing.createData(addr, t);
        return true;
    }

    /** Resolve a base type spec (no pointers/arrays): a scalar keyword, a
     *  `struct X`, or a typedef/enum name already in the DTM. */
    private DataType resolveBaseType(DataTypeManager dtm, String spec) {
        spec = spec.replaceAll("\\s+", " ").trim();
        if (spec.startsWith("struct ")) {
            return findComposite(dtm, spec.substring(7).trim());
        }
        switch (spec) {
            case "int": case "signed int": case "signed":
                return IntegerDataType.dataType;
            case "unsigned int": case "unsigned":
                return UnsignedIntegerDataType.dataType;
            case "char":            return CharDataType.dataType;
            case "unsigned char":   return UnsignedCharDataType.dataType;
            case "signed char":     return SignedCharDataType.dataType;
            case "short": case "short int":
                return ShortDataType.dataType;
            case "unsigned short": case "unsigned short int":
                return UnsignedShortDataType.dataType;
            case "long": case "long int":
                return LongDataType.dataType;
            case "unsigned long":   return UnsignedLongDataType.dataType;
            case "void":            return null;
        }
        // typedef / enum by name
        List<DataType> f = new ArrayList<>();
        dtm.findDataTypes(spec, f);
        for (DataType d : f) {
            if (!(d instanceof FunctionDefinition) && d.getLength() > 0) return d;
        }
        return null;
    }

    private DataType findComposite(DataTypeManager dtm, String name) {
        List<DataType> f = new ArrayList<>();
        dtm.findDataTypes(name, f);
        for (DataType d : f) {
            if (d instanceof Composite && d.getLength() > 0) return d;
        }
        return null;
    }

    // General helpers

    /**
     * True if {@code addr} lies within the span of some debug-symbol
     * function.  Debug functions are laid out contiguously, so an address
     * belongs to a named function whenever it is at or after the first
     * code-symbol address and still inside the code object.  Addresses
     * before the first symbol are genuine gaps (e.g. ___begtext padding).
     */
    private boolean isDebugCovered(long addr, TreeSet<Long> dbgAddrs, long codeEndExcl) {
        Long floor = dbgAddrs.floor(addr);
        return floor != null && addr < codeEndExcl;
    }

    private String findSymbolsJson() throws Exception {
        try {
            String scriptPath = getSourceFile().getAbsolutePath();
            File scriptDir = new File(scriptPath).getParentFile();
            File repoDir = scriptDir.getParentFile();
            // New location: data/out/symbols.json
            File candidate = new File(repoDir, "data/out/symbols.json");
            if (candidate.exists()) {
                return candidate.getAbsolutePath();
            }
            // Legacy fallback: disasm/symbols.json
            File legacy = new File(repoDir, "disasm/symbols.json");
            if (legacy.exists()) {
                return legacy.getAbsolutePath();
            }
        } catch (Exception e) {
            // getSourceFile() may not be available in all contexts
        }

        File f = askFile("Select symbols.json (in data/out/ directory)", "Select");
        if (f != null && f.exists()) {
            return f.getAbsolutePath();
        }
        return null;
    }

    /**
     * Resolve a source-level calling convention name to a Ghidra-recognized name.
     * See x86watcom.cspec for the __watcall definition.
     */
    private String resolveCallingConvention(String sourceName, FunctionManager funcMgr) {
        if (conventionCache.containsKey(sourceName)) {
            return conventionCache.get(sourceName);
        }

        ghidra.program.model.lang.PrototypeModel[] models =
            currentProgram.getCompilerSpec().getCallingConventions();
        List<String> available = new ArrayList<>();
        for (ghidra.program.model.lang.PrototypeModel m : models) {
            available.add(m.getName());
        }

        String[] candidates;
        if ("__watcall".equals(sourceName)) {
            candidates = new String[] {
                "__watcall",
                "__watcallcall",
                "__register",
            };
        } else {
            candidates = new String[] { sourceName };
        }

        String resolved = null;
        for (String candidate : candidates) {
            if (available.contains(candidate)) {
                resolved = candidate;
                break;
            }
        }

        if (resolved == null && !conventionCache.containsKey(sourceName)) {
            println("  Available conventions: " + available);
            println("  No match for '" + sourceName + "' — skipping");
        }

        conventionCache.put(sourceName, resolved);
        return resolved;
    }

    /**
     * Match a string against a pattern with * wildcard support.
     * Patterns:
     *   "D:\\C2\\CODE\\*" — matches any string starting with "D:\C2\CODE\"
     *   "aila.asm"        — exact match
     *   "*smack*"         — contains "smack"
     */
    private static boolean matchesPattern(String text, String pattern) {
        if (text == null || pattern == null) return false;
        if (pattern.endsWith("*") && !pattern.startsWith("*")) {
            return text.startsWith(pattern.substring(0, pattern.length() - 1));
        }
        if (pattern.startsWith("*") && !pattern.endsWith("*")) {
            return text.endsWith(pattern.substring(1));
        }
        if (pattern.startsWith("*") && pattern.endsWith("*") && pattern.length() > 2) {
            return text.contains(pattern.substring(1, pattern.length() - 1));
        }
        return text.equals(pattern);
    }
}
