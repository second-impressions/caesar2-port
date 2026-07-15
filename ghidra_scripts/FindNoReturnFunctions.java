// Find all functions marked as noreturn and check if they actually end with JMP
// (shared epilogue pattern) vs truly noreturn functions.
// @category Caesar2

import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;

public class FindNoReturnFunctions extends GhidraScript {
    @Override
    public void run() throws Exception {
        FunctionManager funcMgr = currentProgram.getFunctionManager();
        int noreturnCount = 0;
        int jmpEndCount = 0;
        int trueNoreturnCount = 0;

        println("Functions marked noreturn:");
        FunctionIterator iter = funcMgr.getFunctions(true);
        while (iter.hasNext()) {
            Function func = iter.next();
            if (!func.hasNoReturn()) continue;
            noreturnCount++;

            // Check the last instruction of the function
            Instruction lastInstr = null;
            InstructionIterator instrIter = currentProgram.getListing()
                .getInstructions(func.getBody(), true);
            while (instrIter.hasNext()) {
                lastInstr = instrIter.next();
            }

            String lastMnem = lastInstr != null ? lastInstr.getMnemonicString() : "?";
            boolean endsWithJmp = lastMnem.startsWith("JMP");

            if (endsWithJmp) {
                jmpEndCount++;
                println(String.format("  JMP-end: %s @ %s  (last: %s %s)",
                    func.getName(), func.getEntryPoint(),
                    lastMnem, lastInstr.getDefaultOperandRepresentation(0)));
            } else {
                trueNoreturnCount++;
                println(String.format("  TRUE:    %s @ %s  (last: %s)",
                    func.getName(), func.getEntryPoint(), lastMnem));
            }
        }

        println("\nTotal noreturn: " + noreturnCount);
        println("  JMP-end (shared epilogue): " + jmpEndCount);
        println("  True noreturn:             " + trueNoreturnCount);
    }
}
