# Linker Guide


## Index of Topics

- # - The # Directive 

- 1 - 1014 stack segment not found 
1019 segment relocation at %a 
1023 no starting address found, using %a 
1027 redefinition of %S ignored 
1028 %S is an undefined reference 
1032 record (type 0x%x) not processed 
1038 DEBUG directive appears after object files 
1043 duplicate exported ordinal 
1044,2044 exported symbol %s not found 
1045 segment attribute defined more than once 
1046 segment name %s not found 
1047 class name %s not found 
1048 inconsistent attributes for automatic data segment 
1050 invalid DLL specified in OLDLIBRARY option 
1054 debugging information incompatible:  using line numbers only 
1058 %s option not valid for %s executable 
1059,2059 value for %s too large 
1060 value for %s incorrect 
1061 multiple values specified for REALBREAK 
1062 DLL COMENT record invalid when not in OS2 
1069 unload CHECK procedure not found 
1072 SECTION directive not allowed in root 
1076 %s option multiply specified 
1080 file %s is a 32-bit object file 
1087 stack segment ignored in .COM file 
1090 redefinition of %s by %s ignored 
1095 debugging information too large. 
1098 Phar Lap offset option must be a multiple of 4K 
1101 cannot use both option verbose and a trace directive 
1102 object file %s not found for tracing 
1103 library module %s(%s) not found for tracing 
1105 cannot reserve %l bytes of extra overlay space 
1107 undefined system name:  %s 
1108 system %s defined more than once 
1110 library members not allowed in libfile 
1111 error in default system block 
1115 environment name %s not found 
1116 overlay area must be at least %l bytes 
1117 segment number too high for a movable entry point 
1118 heap size too large 
1121 '%s' has already been exported 
1124 lazy reference for %S has different default resolutions 
1125 multiple aliases found for %S 
1126 INT 15 interrupt may be incorrect 
1130 %s is an invalid shared nlm file 
1133 no realbreak specified for 16-bit code 
1134 %s is an invalid message file 
1136 relocation to a read/write data segment found at %a 
1140 invalid message number 
1141 virtual function table record for %s mismatched 
1143 not enough memory to sort map file symbols 
1145 %S is both pure virtual and non-pure virtual 
1148 Invalid segment type specified 
1149 Only one debugging format can be specified 

- 2 - 2002 ** internal ** - %s 
2008 cannot open %s :  %s 
2010,3010 I/O error processing %s :  %s 
2011 invalid object file attribute 
2012 invalid library file attribute 
2015 bad location specified in FIXUP 
2016 %a:  absolute target invalid for self-relative relocation 
2017 bad location specified for self-relative relocation at %a 
2018 relocation offset at %a is out of range 
2020 size of group %s exceeds 64k by %l bytes 
2021 size of segment %s exceeds 64k by %l bytes 
2022 cannot have a starting address with an imported symbol 
2024 missing overlay loader 
2025 short vector %d is out of range 
2026 redefinition of reserved symbol %s 
2029 premature end of file encountered 
2030 multiple starting addresses found 
2031 segment %s is in group %s and group %s 
2033,3033 directive error near '%s' 
2034 %a cannot have an offset with an imported symbol 
2039 ALIGNMENT value too small 
2040 ordinal in IMPORT directive not valid 
2041 ordinal in EXPORT directive not valid 
2042 too many IOPL words in EXPORT directive 
2049 invalid STUB file 
2051 STUB file name same as executable file name 
2052 relocation at %a not in the same segment 
2053 %a:  cannot reach a DLL with a relative relocation 
2055 %a:  frame must be the same as the target in protected mode 
2056 cannot find library member %s(%s) 
2063 invalid relocation for flat memory model at %a 
2064 cannot combine 32-bit segments with 16-bit segments 
2065 REALBREAK symbol %s not found 
2066 invalid relative relocation type for an import at %a 
2067 %a:  cannot relocate between code and data in Novell formats 
2068 absolute segment fixup not valid in protected mode 
2070 START procedure not found 
2071 EXIT procedure not found 
2073 bad Novell file format specified 
2074 invalid NLM description 
2075 expecting an END directive 
2082 invalid record type 0x%x 
2083 cannot reference address %a from frame %x 
2084 target offset exceeds 64K at %a 
2086 invalid starting address for .COM file 
2089 program too large for a .COM file 
2091 group %s is in more than one overlay 
2092 NEWSEGMENT directive appears before object files 
2093 cannot open %s 
2094 i/o error processing %s 
2099 symbol name too long:  %s 
2119 wlib import statement incorrect 
2120 application too large to run under DOS 
2127 cannot export absolute symbol %S 
2132 curly brace delimited list incorrect 
2146 %s is an invalid object file 

- 3 - 3009 dynamic memory exhausted 
3013 break key detected 
3057 executable format has been established 
3088 virtual memory exhausted 
3096 incompatible types of debugging information found 
3097 too many library modules 
3109 system block %s too large 
3114 environment name specified incorrectly 
3122 no FILE directives found 
3123 OS/2 offset option must be a multiple of 64K 
3126 too many EMS requests queued 
3128 directive error near beginning of input 
3129 address information too large 
3131 cannot open spill file:  file already exists 
3135 need exactly 1 overlay area with dynamic overlay manager 
3137 too many errors encountered 
3138 invalid filename '%s' 
3139 cannot have both 16-bit and 32-bit object files 
3147 Ambiguous format specified 

- @ - The @ Directive 

- A - All Debugging Information - DEBUG ALL 
The ARTIFICIAL Option 

- C - The CACHE Option 
The CASEEXACT Option 
Converting Libraries Created using Phar Lap 386|LIB 

- D - The DEBUG Directive 
The DISABLE Directive 
DOS:  Converting Microsoft Response Files to Directive Files 
DOS:  Defining Overlay Structures 
DOS:  How Overlay Files are Opened 
DOS:  Increasing the Dynamic Overlay Area 
DOS:  Memory Layout 
DOS:  Nested Overlay Structures 
DOS:  Rules About Overlays 
DOS:  The AREA Option 
DOS:  The AUTOSECTION Directive 
DOS:  The BEGIN and END Directives 
DOS:  The DISTRIBUTE Option 
DOS:  The DOS Executable File Format 
DOS:  The DYNAMIC Option 
DOS:  The Dynamic Overlay Manager 
DOS:  The FIXEDLIB Directive 
DOS:  The FORCEVECTOR Directive 
DOS:  The FORMAT Directive 
DOS:  The NOINDIRECT Option 
DOS:  The NOVECTOR Directive 
DOS:  The OPTION Directive 
DOS:  The OVERLAY Directive 
DOS:  The PACKDATA Option 
DOS:  The SECTION Directive 
DOS:  The SMALL Option 
DOS:  The STANDARD Option 
DOS:  The VECTOR Directive 
DOS:  The WATCOM Linker Command Line 
DOS:  The WATCOM Linker Memory Requirements 
DOS:  Using Overlays 
DOS:  WATCOM Linker Directives 
The DOSSEG Option 

- E - ELF:  Memory Layout 
ELF:  The ALIGNMENT Option 
ELF:  The ELF Executable File Format 
ELF:  The EXPORT Directive 
ELF:  The FORMAT Directive 
ELF:  The IMPORT Directive 
ELF:  The MODULE Directive 
ELF:  The OPTION Directive 
ELF:  The WATCOM Linker Command Line 
ELF:  The WATCOM Linker Memory Requirements 
ELF:  WATCOM Linker Directives 
The ELIMINATE Option 

- F - The FILE Directive 
The FORMAT Directive 

- G - General Directives and Options 
Global Symbol Information 
Global Symbols for the NetWare 386 Debugger - DEBUG NOVELL 

- I - Introduction 

- L - The LANGUAGE Directive 
The LIBFILE Directive 
The LIBPATH Directive 
The LIBRARY Directive 
Line Numbering Information - DEBUG LINES 
Linker Error Messages 
Linking 16-bit DOS .COM Executable Files 
Linking 16-bit DOS Executable Files 
Linking 16-bit Executable Files 
Linking 16-bit OS/2 Dynamic Link Libraries 
Linking 16-bit OS/2 Executable Files 
Linking 16-bit QNX Executable Files 
Linking 16-bit Windows Dynamic Link Libraries 
Linking 16-bit Windows Executable Files 
Linking 32-bit AutoCAD Development System Executable Files 
Linking 32-bit AutoCAD Device Interface Executable Files 
Linking 32-bit DOS/4GW Executable Files 
Linking 32-bit Executable Files 
Linking 32-bit FlashTek Executable Files 
Linking 32-bit Novell NetWare Loadable Modules 
Linking 32-bit OS/2 Dynamic Link Libraries 
Linking 32-bit OS/2 Executable Files 
Linking 32-bit OS/2 Presentation Manager Executable Files 
Linking 32-bit Phar Lap Executable Files 
Linking 32-bit Phar Lap TNT Executable Files 
Linking 32-bit QNX Executable Files 
Linking 32-bit Windows Dynamic Link Libraries 
Linking 32-bit Windows Executable 
Linking 32-bit Windows NT Character-Mode Executable Files 
Linking 32-bit Windows NT Dynamic Link Libraries 
Linking 32-bit Windows NT Windowed Executable Files 
Linking Executable Files for Various Systems 
Local Symbol Information - DEBUG LOCALS 

- M - The MANGLEDNAMES Option 
The MAP Option 
The MAXERRORS Option 
The MODTRACE Directive 

- N - The NAME Directive 
The NAMELEN Option 
NetWare:  Memory Layout 
NetWare:  NetWare Loadable Modules 
NetWare:  The CHECK Option 
NetWare:  The COPYRIGHT Option 
NetWare:  The CUSTOM Option 
NetWare:  The EXIT Option 
NetWare:  The EXPORT Directive 
NetWare:  The FORMAT Directive 
NetWare:  The IMPORT Directive 
NetWare:  The MODULE Directive 
NetWare:  The MULTILOAD Option 
NetWare:  The NetWare 386 Executable File Format 
NetWare:  The OPTION Directive 
NetWare:  The PSEUDOPREEMPTION Option 
NetWare:  The REENTRANT Option 
NetWare:  The SCREENNAME Option 
NetWare:  The START Option 
NetWare:  The SYNCHRONIZE Option 
NetWare:  The THREADNAME Option 
NetWare:  The VERSION Option 
NetWare:  The WATCOM Linker Command Line 
NetWare:  The WATCOM Linker Memory Requirements 
NetWare:  WATCOM Linker Directives 
The NEWSEGMENT Directive 
The NODEFAULTLIBS Option 
NT:  Creating a Dynamic Link Library 
NT:  Dynamic Link Libraries 
NT:  Memory Layout 
NT:  The ALIAS Directive 
NT:  The ALIGNMENT Option 
NT:  The COMMIT Directive 
NT:  The DESCRIPTION Option 
NT:  The EXPORT Directive 
NT:  The FORMAT Directive 
NT:  The HEAPSIZE Option 
NT:  The IMPORT Directive 
NT:  The MANYAUTODATA Option 
NT:  The MODNAME Option 
NT:  The NOAUTODATA Option 
NT:  The OBJALIGN Option 
NT:  The OLDLIBRARY Option 
NT:  The ONEAUTODATA Option 
NT:  The OPTION Directive 
NT:  The PACKDATA Option 
NT:  The REFERENCE Directive 
NT:  The RUNTIME Directive 
NT:  The SEGMENT Directive 
NT:  The SORT Directive 
NT:  The STUB Option 
NT:  The VERSION Option 
NT:  The WATCOM Linker Command Line 
NT:  The WATCOM Linker Memory Requirements 
NT:  The Windows NT Executable and DLL File Formats 
NT:  Using a Dynamic Link Library 
NT:  WATCOM Linker Directives 

- O - The ONLYEXPORTS Debugging Option 
The OPTION Directive 
OS/2:  Converting Microsoft Response Files to Directive Files 
OS/2:  Creating a Dynamic Link Library 
OS/2:  Dynamic Link Libraries 
OS/2:  Memory Layout 
OS/2:  The ALIAS Directive 
OS/2:  The ALIGNMENT Option 
OS/2:  The DESCRIPTION Option 
OS/2:  The EXPORT Directive 
OS/2:  The FORMAT Directive 
OS/2:  The HEAPSIZE Option 
OS/2:  The IMPORT Directive 
OS/2:  The INTERNALRELOCS Option 
OS/2:  The MANYAUTODATA Option 
OS/2:  The MODNAME Option 
OS/2:  The NEWFILES Option 
OS/2:  The NOAUTODATA Option 
OS/2:  The OFFSET Option 
OS/2:  The OLDLIBRARY Option 
OS/2:  The ONEAUTODATA Option 
OS/2:  The OPTION Directive 
OS/2:  The OS/2 Executable and DLL File Formats 
OS/2:  The PACKDATA Option 
OS/2:  The PROTMODE Option 
OS/2:  The REFERENCE Directive 
OS/2:  The SEGMENT Directive 
OS/2:  The SORT Directive 
OS/2:  The STUB Option 
OS/2:  The VERSION Option 
OS/2:  The WATCOM Linker Command Line 
OS/2:  The WATCOM Linker Memory Requirements 
OS/2:  Using a Dynamic Link Library 
OS/2:  WATCOM Linker Directives 
The OSNAME Option 

- P - The PACKCODE Option 
The PATH Directive 
Phar Lap:  32-bit Protected-Mode Applications 
Phar Lap:  Memory Layout 
Phar Lap:  Memory Usage 
Phar Lap:  The FORMAT Directive 
Phar Lap:  The MAXDATA Option 
Phar Lap:  The MINDATA Option 
Phar Lap:  The OFFSET Option 
Phar Lap:  The OPTION Directive 
Phar Lap:  The Phar Lap Executable File Format 
Phar Lap:  The RUNTIME Directive 
Phar Lap:  The WATCOM Linker Command Line 
Phar Lap:  The WATCOM Linker Memory Requirements 
Phar Lap:  WATCOM Linker Directives 

- Q - QNX:  Memory Layout 
QNX:  The ALIAS Directive 
QNX:  The FORMAT Directive 
QNX:  The HEAPSIZE Option 
QNX:  The LINEARRELOCS Option 
QNX:  The LONGLIVED Option 
QNX:  The NORELOCS Option 
QNX:  The OFFSET Option 
QNX:  The OPTION Directive 
QNX:  The PACKDATA Option 
QNX:  The PRIVILEGE Option 
QNX:  The QNX Executable File Format 
QNX:  The REFERENCE Directive 
QNX:  The RESOURCE Option 
QNX:  The SEGMENT Directive 
QNX:  The SORT Directive 
QNX:  The WATCOM Linker Command Line 
QNX:  The WATCOM Linker Memory Requirements 
QNX:  WATCOM Linker Directives 
The QUIET Option 

- R - The REDEFSOK Option 
Removing Debugging Information from an Executable File 

- S - Searching for Libraries Specified in Environment Variables 
Special System Names 
The STACK Option 
The STATIC Option 
Static Symbol Information - DEBUG STATIC 
The SYMFILE Option 
The SYMTRACE Directive 
The SYSTEM Directive 

- T - Typing Information - DEBUG TYPES 

- U - The UNDEFSOK Option 
Using DEBUG Directives 

- V - The VERBOSE Option 

- W - Windows:  Converting Microsoft Response Files to Directive Files 
Windows:  Creating a Dynamic Link Library 
Windows:  Discardable Segments 
Windows:  Dynamic Link Libraries 
Windows:  Fixed and Moveable Segments 
Windows:  Memory Layout 
Windows:  The ALIAS Directive 
Windows:  The ALIGNMENT Option 
Windows:  The DESCRIPTION Option 
Windows:  The EXPORT Directive 
Windows:  The FORMAT Directive 
Windows:  The HEAPSIZE Option 
Windows:  The IMPORT Directive 
Windows:  The MANYAUTODATA Option 
Windows:  The MODNAME Option 
Windows:  The NOAUTODATA Option 
Windows:  The OLDLIBRARY Option 
Windows:  The ONEAUTODATA Option 
Windows:  The OPTION Directive 
Windows:  The PACKDATA Option 
Windows:  The REFERENCE Directive 
Windows:  The RWRELOCCHECK Option 
Windows:  The SEGMENT Directive 
Windows:  The SORT Directive 
Windows:  The STUB Option 
Windows:  The VERSION Option 
Windows:  The WATCOM Linker Command Line 
Windows:  The WATCOM Linker Memory Requirements 
Windows:  The Windows Executable and DLL File Formats 
Windows:  Using a Dynamic Link Library 
Windows:  WATCOM Linker Directives


## Introduction

The WATCOM Linker is a linkage editor (linker) that takes object and library files as input and produces executable files as output.  The following object module formats are supported by the WATCOM Linker. 

oThe standard Intel object module format. 
oMicrosoft's extensions to the Intel standard object module format. 
oPhar Lap's Easy OMF-386 object module format for linking 386 applications. 
The WATCOM Linker is capable of producing a number of executable file formats.  The following lists these executable file formats. 

oDOS executable files 
oexecutable files that run under FlashTek's DOS extender 
oexecutable files that run under Phar Lap's 386|DOS-Extender 
oexecutable files that run under Tenberry Software's DOS/4G and DOS/4GW DOS extenders 
oexecutable files that run under AutoDesk's AutoCAD Development System 
oNetWare Loadable Modules (NLMs) that run under Novell's NetWare 386 operating system 
oOS/2 executable files including dynamic link libraries 
oQNX executable files 
oWindows 3.x executable files including dynamic link libraries 
oWindows NT executable files including dynamic link libraries 
In addition to being able to generate the above executable file formats, the WATCOM Linker also runs under a variety of operating systems.  Currently, the WATCOM Linker runs under the following operating systems. 

oDOS 
oOS/2 
oQNX 
oWindows NT 
The chapter entitled Linking Executable Files for Various Systems summarizes each of the executable file formats that can be generated by the linker.  The chapter entitled General Directives and Options describes the linker directives that are common to all executable file formats.  Then there is one chapter devoted to each particular executable file format. 
We refer to the operating system upon which you run the WATCOM Linker as the "host".  Where possible, host-specific information is discussed.  Note that, for conciseness, the examples given are specific to the host operating system for which the executable file is intended.  For example, the chapter entitled DOS:  The DOS Executable File Format contains examples that describe the usage of a DOS-hosted version of the WATCOM Linker and the chapter entitled QNX:  The QNX Executable File Format contains examples that describe the usage of a QNX-hosted version of the WATCOM Linker.  If you wish to create QNX applications with the DOS-hosted version of the WATCOM Linker or wish to create DOS applications with the QNX-hosted version of the WATCOM Linker, the examples must be adapted to reflect the host operating system.


## Linking Executable Files for Various Systems

For each executable file format that can be created using the WATCOM Linker, a specific SYSTEM directive may be used.  The SYSTEM directive selects a subset of the available directives necessary to create each specific executable file format. 

com 16-bit DOS ".COM" executable 

dos 16-bit DOS executable 

dos4g 32-bit DOS/4GW executable 

netware 32-bit NetWare Loadable Module 

os2 16-bit OS/2 executable 

os2 dll 16-bit OS/2 Dynamic Link Library 

os2v2 32-bit OS/2 executable 

os2v2 dll 32-bit OS/2 Dynamic Link Library 

os2v2_pm 32-bit OS/2 Presentation Manager executable 

pharlap 32-bit Phar Lap executable 

tnt 32-bit Phar Lap TNT executable 

qnx 16-bit QNX executable 

qnx386 32-bit QNX executable 

x32r 32-bit FlashTek executable using register-based calling conventions 

x32rv 32-bit virtual-memory FlashTek executable using register-based calling conventions 

x32s 32-bit FlashTek executable using stack-based calling conventions 

x32sv 32-bit virtual-memory FlashTek executable using stack-based calling conventions 

windows 16-bit Windows executable 

windows_dll 16-bit Windows Dynamic Link Library 

win386 32-bit WATCOM Windows-extender executable or Dynamic Link Library 

nt 32-bit Windows NT character-mode executable 

nt_win 32-bit Windows NT windowed executable 

nt_dll 32-bit Windows NT Dynamic Link Library 

ads 32-bit AutoCAD Development System executable 

eadi 32-bit Emulation AutoCAD Device Interface 

fadi 32-bit Floating-point AutoCAD Device Interface 
In the following sections, we show some of the typical directives that you might use to create a particular executable file format.  The common directives are described in the chapter entitled General Directives and Options.  They are "common" in the sense that they may be used with any executable format.  There are other, less general, directives that may be specified for a particular executable format.  In each of the following sections, we refer you to chapters in which you will find more information on the directives available with the executable format used. 
At this point, it should be noted that various systems have adopted particular executable file formats.  For example, AutoCAD applications use a Phar Lap executable file format and both the Tenberry Software DOS/4G(W) and FlashTek DOS extenders support one of the OS/2 executable file formats.  It is for this reason that you may find that we direct you to a chapter which would, at first glance, seem unrelated to the executable file format in which you are interested. 
To summarize, the steps that you should follow to learn about creating a particular executable are: 

 1.Look for a section in this chapter that describes the executable format in which you are interested. 

 2.See the chapter entitled General Directives and Options for a description of the common directives. 

 3.If you require additional information, see also the chapter to which we have referred you. 

 4.Also check the WATCOM Programmer's Guide for more information on creating specific types of applications.


### Linking 16-bit Executable Files

The following sections describe how to link a variety of 16-bit executable files.


#### Linking 16-bit DOS Executable Files

To create this type of file, use the following structure. 
    
   system  dos 
   option  map 
   name   app_name 
   file   obj1, obj2, ... 
   library  lib1, lib2, ... 
For more information, see the chapter entitled DOS:  The DOS Executable File Format.


#### Linking 16-bit DOS .COM Executable Files

To create this type of file, use the following structure. 
    
   system  com 
   option  map 
   name   app_name 
   file   obj1, obj2, ... 
   library  lib1, lib2, ... 
For more information, see the chapter entitled DOS:  The DOS Executable File Format.


#### Linking 16-bit OS/2 Executable Files

To create this type of file, use the following structure. 
    
   system  os2 
   option  map 
   name   app_name 
   file   obj1, obj2, ... 
   library  lib1, lib2, ... 
For more information, see the chapter entitled OS/2:  The OS/2 Executable and DLL File Formats.


#### Linking 16-bit OS/2 Dynamic Link Libraries

To create this type of file, use the following structure. 
    
   system  os2 dll 
   option  map 
   name   app_name 
   file   obj1, obj2, ... 
   library  lib1, lib2, ... 
For more information, see the chapter entitled OS/2:  The OS/2 Executable and DLL File Formats.


#### Linking 16-bit QNX Executable Files

To create this type of file, use the following structure. 
    
   system  qnx 
   option  map 
   name   app_name 
   file   obj1, obj2, ... 
   library  lib1, lib2, ... 
For more information, see the chapter entitled QNX:  The QNX Executable File Format.


#### Linking 16-bit Windows Executable Files

To create this type of file, use the following structure. 
    
   system  windows 
   option  map 
   name   app_name 
   file   obj1, obj2, ... 
   library  lib1, lib2, ... 
For more information, see the chapter entitled Windows:  The Windows Executable and DLL File Formats.


#### Linking 16-bit Windows Dynamic Link Libraries

To create this type of file, use the following structure. 
    
   system  windows_dll 
   option  map 
   name   app_name 
   file   obj1, obj2, ... 
   library  lib1, lib2, ... 
For more information, see the chapter entitled Windows:  The Windows Executable and DLL File Formats.


### Linking 32-bit Executable Files

The following sections describe how to create a variety of 32-bit executable files.


#### Linking 32-bit AutoCAD Development System Executable Files

To create this type of file, use the following structure. 
    
   system  ads 
   option  map 
   name   app_name 
   file   obj1, obj2, ... 
   library  lib1, lib2, ... 
For more information, see the chapter entitled Phar Lap:  The Phar Lap Executable File Format.


#### Linking 32-bit AutoCAD Device Interface Executable Files

To create this type of file, use the following structure for an emulation AutoCAD Device Interface. 
    
   system  eadi 
   option  map 
   name   app_name 
   file   obj1, obj2, ... 
   library  lib1, lib2, ... 
To create a floating-point AutoCAD Device Interface, specify 
    
   system  fadi. 
For more information, see the chapter entitled Phar Lap:  The Phar Lap Executable File Format.


#### Linking 32-bit DOS/4GW Executable Files

To create this type of file, use the following structure. 
    
   system  dos4g 
   option  map 
   name   app_name 
   file   obj1, obj2, ... 
   library  lib1, lib2, ... 
For more information, see the chapter entitled OS/2:  The OS/2 Executable and DLL File Formats.


#### Linking 32-bit FlashTek Executable Files

To create these files, use one of the following structures. 
    
   system  x32r 
   option  map 
   name   app_name 
   file   obj1, obj2, ... 
   library  lib1, lib2, ... 
If the system is x32r, a FlashTek executable file is created for an application using the register calling convention. 
    
   system  x32rv 
   option  map 
   name   app_name 
   file   obj1, obj2, ... 
   library  lib1, lib2, ... 
If the system is x32rv, a virtual-memory FlashTek executable file is created for an application using the register calling convention. 
    
   system  x32s 
   option  map 
   name   app_name 
   file   obj1, obj2, ... 
   library  lib1, lib2, ... 
If the system is x32s, a FlashTek executable file is created for an application using the stack calling convention. 
    
   system  x32sv 
   option  map 
   name   app_name 
   file   obj1, obj2, ... 
   library  lib1, lib2, ... 
If the system is x32sv, a virtual-memory FlashTek executable file is created for an application using the stack calling convention. 
For more information, see the chapter entitled OS/2:  The OS/2 Executable and DLL File Formats.


#### Linking 32-bit Novell NetWare Loadable Modules

To create this type of file, use the following structure. 
    
   system  netware 
   option  map 
   name   app_name 
   file   obj1, obj2, ... 
   library  lib1, lib2, ... 
For more information, see the chapter entitled NetWare:  The NetWare 386 Executable File Format.


#### Linking 32-bit OS/2 Executable Files

To create this type of file, use the following structure. 
    
   system  os2v2 
   option  map 
   name   app_name 
   file   obj1, obj2, ... 
   library  lib1, lib2, ... 
For more information, see the chapter entitled OS/2:  The OS/2 Executable and DLL File Formats.


#### Linking 32-bit OS/2 Dynamic Link Libraries

To create this type of file, use the following structure. 
    
   system  os2v2 dll 
   option  map 
   name   app_name 
   file   obj1, obj2, ... 
   library  lib1, lib2, ... 
For more information, see the chapter entitled OS/2:  The OS/2 Executable and DLL File Formats.


#### Linking 32-bit OS/2 Presentation Manager Executable Files

To create this type of file, use the following structure. 
    
   system  os2v2_pm 
   option  map 
   name   app_name 
   file   obj1, obj2, ... 
   library  lib1, lib2, ... 
For more information, see the chapter entitled OS/2:  The OS/2 Executable and DLL File Formats.


#### Linking 32-bit Phar Lap Executable Files

To create this type of file, use the following structure. 
    
   system  pharlap 
   option  map 
   name   app_name 
   file   obj1, obj2, ... 
   library  lib1, lib2, ... 
For more information, see the chapter entitled Phar Lap:  The Phar Lap Executable File Format.


#### Linking 32-bit Phar Lap TNT Executable Files

To create this type of file, use the following structure. 
    
   system  tnt 
   option  map 
   name   app_name 
   file   obj1, obj2, ... 
   library  lib1, lib2, ... 
For more information, see the chapter entitled NT:  The Windows NT Executable and DLL File Formats.


#### Linking 32-bit QNX Executable Files

To create this type of file, use the following structure. 
    
   system  qnx386 
   option  map 
   name   app_name 
   file   obj1, obj2, ... 
   library  lib1, lib2, ... 
For more information, see the chapter entitled QNX:  The QNX Executable File Format.


#### Linking 32-bit Windows Executable

To create this type of file, use the following structure. 
    
   system  win386 
   option  map 
   name   app_name 
   file   obj1, obj2, ... 
   library  lib1, lib2, ... 
After linking this executable, you must bind the WATCOM Windows-extender to the executable (a .REX file) to produce a Windows executable (a .EXE file). 
    
   wbind -n app_name 
For more information, see the chapter entitled Windows:  The Windows Executable and DLL File Formats.


#### Linking 32-bit Windows Dynamic Link Libraries

To create this type of file, use the following structure. 
    
   system  win386 
   option  map 
   name   app_name 
   file   obj1, obj2, ... 
   library  lib1, lib2, ... 
After linking this executable, you must bind the WATCOM Windows-extender for DLLs to the executable (a .REX file) to produce a Windows Dynamic Link Library (a .DLL file). 
    
   wbind -n -d app_name 
For more information, see the chapter entitled Windows:  The Windows Executable and DLL File Formats.


#### Linking 32-bit Windows NT Character-Mode Executable Files

To create this type of file, use the following structure. 
    
   system  nt 
   option  map 
   name   app_name 
   file   obj1, obj2, ... 
   library  lib1, lib2, ... 
For more information, see the chapter entitled NT:  The Windows NT Executable and DLL File Formats.


#### Linking 32-bit Windows NT Windowed Executable Files

To create this type of file, use the following structure. 
    
   system  nt_win 
   option  map 
   name   app_name 
   file   obj1, obj2, ... 
   library  lib1, lib2, ... 
For more information, see the chapter entitled NT:  The Windows NT Executable and DLL File Formats.


#### Linking 32-bit Windows NT Dynamic Link Libraries

To create this type of file, use the following structure. 
    
   system  nt_dll 
   option  map 
   name   app_name 
   file   obj1, obj2, ... 
   library  lib1, lib2, ... 
For more information, see the chapter entitled NT:  The Windows NT Executable and DLL File Formats.


## General Directives and Options

For each executable file format that the WATCOM Linker produces, certain directives and options are common to each.  The following is a list of the common directives and options, in alphabetical order.  The sections that follow provide detailed descriptions of the items in this list.  The sections are also ordered alphabetically. 

DEBUG [[WATCOM] db_list | CODEVIEW | DWARF] 

DISABLE msg_num{,msg_num} 

FILE obj_spec{,obj_spec} 

FORMAT form 

LANGUAGE lang 

LIBFILE obj_file{,obj_file} 

LIBPATH path_name{;path_name} 

LIBRARY library_file{,library_file} 

MODTRACE obj_module{,obj_module} 

NAME exe_file 

NEWSEGMENT 

OPTION option{,option} 

ARTIFICIAL 

[NO]CACHE 

[NO]CASEEXACT 

DOSSEG 

ELIMINATE 

MANGLEDNAMES 

MAP[=map_file] 

MAXERRORS=n 

NAMELEN=n 

NODEFAULTLIBS 

OSNAME='string' 

PACKCODE=n 

QUIET 

REDEFSOK 

STACK=n 

STATIC 

SYMFILE[=symbol_file] 

UNDEFSOK 

VERBOSE 

PATH path_name{;path_name} 

SYMTRACE symbol_name{,symbol_name} 

SYSTEM BEGIN system_name {directive} END 

SYSTEM system_name 

# comment 

@ directive_file


### The DEBUG Directive

The "DEBUG" directive is used to tell the WATCOM Linker to generate debugging information in the executable file.  This extra information in the executable file is used by the WATCOM Debugger.  The format of the "DEBUG" directive (short form "D") is as follows. 
    
     DEBUG [[WATCOM] db_list | CODEVIEW | DWARF] 
    
     db_list ::= [db_option{,db_option}] 
     db_option ::= LINES | TYPES | LOCALS | STATIC | ALL 
The format for a NetWare executable file differs slightly.  The format is as follows. 
    
     DEBUG [[WATCOM] db_list | CODEVIEW | DWARF] 
       or 
     DEBUG NOVELL [ONLYEXPORTS] [REFERENCED] 
    
     db_list ::= [db_option{,db_option}] 
     db_option ::= LINES | TYPES | LOCALS | STATIC | ALL | ONLYEXPORTS 
The WATCOM Linker supports three types of debugging information, "WATCOM", "CODEVIEW", or "DWARF". 

WATCOM (short form "W") specifies that all object files contain WATCOM format debugging information and that the executable file will contain WATCOM debugging information.  This debugging format is assumed by default when none is specified. This format permits the selection of specific classes of debugging information ( db_list) which are described below. 

CODEVIEW (short form "C") specifies that all object files contain Codeview (CV4) format debugging information and that the executable file will contain Codeview debugging information. 

DWARF (short form "D") specifies that all object files contain Dwarf format debugging information and that the executable file will contain Dwarf debugging information. 
The following lists the classes of debugging information. 

oglobal symbol information 
ostatic symbol information 
oline numbering information 
olocal symbol information 
otyping information 
oNetWare 386 global symbol information 
The following options can be used with the "DEBUG" directive to control which of the above classes of debugging information is included in the executable file. 

LINES (short form "LI") specifies line numbering and global symbol information. 

LOCALS (short form "LO") specifies local and global symbol information. 

TYPES (short form "T") specifies typing and global symbol information. 

STATIC (short form "ST") specifies static and global symbol information. 

ALL (short form "A") specifies all of the above debugging information. 

NOVELL (short form "N") specifies a second form of global symbol information that can only be processed by the NetWare 386 debugger. 

ONLYEXPORTS (short form "ONL") restricts the generation of global symbol information to exported symbols. 

REFERENCED (short form "REF") restricts the generation of symbol information to referenced symbols only. 
 Note:  The position of the "DEBUG" directive is important.  The level of debugging information specified in a "DEBUG" directive only applies to object files and libraries that appear in subsequent "FILE" or "LIBRARY" directives.  For example, if "DEBUG ALL" was the only "DEBUG" directive specified and was also the last linker directive, no debugging information would appear in the executable file. 
Only global and static symbol information is actually produced by the WATCOM Linker; the other three classes of debugging information are extracted from object modules and copied to the executable file.  Therefore, at compile time, you must instruct the compiler to generate local symbol, line numbering and typing information in the object file so that the information can be transferred to the executable file.  If you have asked the WATCOM Linker to produce a particular class of debugging information and it appears that none is present, one of the following conditions may exist. 

 1.The debugging information is not present in the object files. 

 2.The "DEBUG" directive has been misplaced. 
The following sections describe the classes of debugging information.


#### Line Numbering Information - DEBUG LINES

The "DEBUG LINES" option controls the processing of line numbering information.  Line numbering information is the line number and address of the generated code for each line of source code in a particular module.  This allows WATCOM Debugger to perform source-level debugging.  When the WATCOM Linker encounters a "DEBUG" directive with a "LINES" or "ALL" option, line number information for each subsequent object module will be placed in the executable file.  This includes all object modules extracted from object files specified in subsequent "FILE" directives and object modules extracted from libraries specified in subsequent "LIBRARY" or "FILE" directives. 
 Note:  All modules for which line numbering information is requested must have been compiled with the "d1" or "d2" option. 
A subsequent "DEBUG" directive without a "LINES" or "ALL" option terminates the processing of line numbering information.


#### Local Symbol Information - DEBUG LOCALS

The "DEBUG LOCALS" option controls the processing of local symbol information.  Local symbol information is the name and address of all symbols local to a particular module.  This allows WATCOM Debugger to locate these symbols so that you can reference local data and routines by name.  When the WATCOM Linker encounters a "DEBUG" directive with a "LOCALS" or "ALL" option, local symbol information for each subsequent object module will be placed in the executable file.  This includes all object modules extracted from object files specified in subsequent "FILE" directives and object modules extracted from libraries specified in subsequent "LIBRARY" or "FILE" directives. 
 Note:  All modules for which local symbol information is requested must have been compiled with the "d2" option. 
A subsequent "DEBUG" directive without a "LOCALS" or "ALL" option terminates the processing of local symbol information.


#### Typing Information - DEBUG TYPES

The "DEBUG TYPES" option controls the processing of typing information.  Typing information includes a description of all types, structures and arrays that are defined in a module.  This allows WATCOM Debugger to display variables according to their type.  When the WATCOM Linker encounters a "DEBUG" directive with a "TYPES" or "ALL" option, typing information for each subsequent object module will be placed in the executable file.  This includes all object modules extracted from object files specified in subsequent "FILE" directives and object modules extracted from libraries specified in subsequent "LIBRARY" or "FILE" directives. 
 Note:  All modules for which typing information is requested must have been compiled with the "d2" option. 
A subsequent "DEBUG" directive without a "TYPES" or "ALL" option terminates the processing of typing information.


#### Static Symbol Information - DEBUG STATIC

The "DEBUG STATIC" option controls the processing of static symbol information.  Static symbol information consists of all static symbols in your program and their addresses.  This allows WATCOM Debugger to locate these symbols so that you can reference static data in the modules you are debugging.  When the WATCOM Linker encounters a "DEBUG" directive with a "STATIC" or "ALL" option, static symbol information for each subsequent object module will be placed in the executable file.  This includes all object modules extracted from object files specified in subsequent "FILE" directives and object modules extracted from libraries specified in subsequent "LIBRARY" or "FILE" directives. 
 Note:  Static symbol information is a subset of local symbol information.  The major difference is that static symbol information is always available from the object file much like global symbol information, whereas local symbol information requires source to be compiled with the "d2" option. 
A subsequent "DEBUG" directive without a "STATIC" or "ALL" option terminates the processing of static symbol information.


#### All Debugging Information - DEBUG ALL

The "DEBUG ALL" option specifies that "LINES", "LOCALS", "TYPES" and "STATIC" options are requested.  The "LINES" option controls the processing of line numbering information.  The "LOCALS" option controls the processing of local symbol information.  The "TYPES" option controls the processing of typing information.  The "STATIC" option controls the processing of static symbol information.  Each of these options is described in a previous section.  A subsequent "DEBUG" directive without an "ALL" option discontinues those options which are not specified in the list of debug options.


#### Global Symbol Information

Global symbol information consists of all the global symbols in your program and their address.  This allows WATCOM Debugger to locate these symbols so that you can reference global data and routines by name.  When the WATCOM Linker encounters a "DEBUG" directive, global symbol information for all the global symbols appearing in your program is placed in the executable file.


#### Global Symbols for the NetWare 386 Debugger - DEBUG NOVELL

The NetWare 386 operating system has a built-in debugger that can be used to debug programs.  When "DEBUG NOVELL" is specified, the WATCOM Linker will generate global symbol information that can be used by the NetWare 386 debugger.  Note that any line numbering, local symbol, and typing information generated in the executable file will not be recognized by the NetWare 386 debugger.  Also, WSTRIP cannot be used to remove this form of global symbol information from the executable file.


#### The ONLYEXPORTS Debugging Option

The "ONLYEXPORTS" option (short form "ONL") restricts the generation of global symbol information to exported symbols (symbols appearing in an "EXPORT" directive).  If "DEBUG ONLYEXPORTS" is specified, WATCOM Debugger global symbol information is generated only for exported symbols.  If "DEBUG NOVELL ONLYEXPORTS" is specified, NetWare 386 global symbol information is generated only for exported symbols.


#### Using DEBUG Directives

Consider the following directive file. 
    
   debug all 
   file module1 
   debug lines 
   file module2, module3 
   debug 
   library mylib 
It specifies that the following debugging information is to be generated in the executable file. 

 1.global symbol information for your program 

 2.line numbering, typing and local symbol information for the following object files: 
    
   module1.obj 

 3.line numbering information for the following object files: 
    
   module2.obj 
   module3.obj 
Note that if the "DEBUG" directive before the "LIBRARY" directive is not specified, line numbering information for all object modules extracted from the library "mylib.lib" would be generated in the executable file provided the object modules extracted from the library have line numbering information present. 
 Note:  A "DEBUG" directive with no option suppresses the processing of line numbering, local symbol and typing information for all subsequent object modules. 
Debugging information can use a significant amount of disk space.  As shown in the above example, you can select only the class of debugging information you want and for those modules you wish to debug.  In this way, the amount of debugging information in the executable file is minimized and hence the amount of disk space used by the executable file is kept to a minimum. 
As you can see from the above example, the position of the "DEBUG" directive is important when describing the debugging information that is to appear in the executable file. 
 Note:  If you want all classes of debugging information for all files to appear in the executable file you must specify "DEBUG ALL" before any "FILE" and "LIBRARY" directives.


#### Removing Debugging Information from an Executable File

A utility called WSTRIP has been provided which takes as input an executable file and removes the debugging information placed in the executable file by the WATCOM Linker.  Note that global symbol information generated using "DEBUG NOVELL" cannot be removed by WSTRIP. 
For more information on this utility, see the chapter entitled "The Strip Utility" in the WATCOM Tools User's Guide.


### The DISABLE Directive

The "DISABLE" directive is used to disable the display of linker messages. 
The WATCOM Linker issues three classes of messages; fatal errors, errors and warnings.  Each message has a 4-digit number associated with it.  Fatal messages start with the digit 3, error messages start with the digit 2, and warning messages start with the digit 1.  It is possible for a message to be issued as a warning or an error. 
If a fatal error occurs, the linker will terminate immediately and no executable file will be generated. 
If an error occurs, the linker will continue to execute so that all possible errors are issued.  However, no executable file will be generated since these errors do not permit a proper executable file to be generated. 
If a warning occurs, the linker will continue to execute.  A warning message is usually informational and does not prevent the creation of a proper executable file.  However, all warnings should eventually be corrected. 
Note that the behaviour of the linker does not change when a message is disabled.  For example, if a message that normally terminates the linker is disabled, the linker will still terminate but the message describing the reason for the termination will not be displayed.  For this reason, you should only disable messages that are warnings. 
The linker will ignore the severity of the message number.  For example, some messages can be displayed as errors or warnings.  It is not possible to disable the message when it is issued as a warning and display the message when it is issued as an error.  In general, do not specify the severity of the message when specifying a message number. 
The format of the "DISABLE" directive (short form "DISA") is as follows. 
    
     DISABLE msg_num{, msg_num} 

msg_num is a message number.  See the chapter entitled Linker Error Messages for a list of messages and their corresponding numbers. 
The following "DISABLE" directive will disable message 28 (an undefined symbol has been referenced). 
    
   disable 28


### The FILE Directive

The "FILE" directive is used to specify the object files and library modules that the WATCOM Linker is to process.  The format of the "FILE" directive (short form "F") is as follows. 
    
     FILE obj_spec{,obj_spec} 
     obj_spec ::= obj_file[(obj_module)] 
              | library_file[(obj_module)] 

obj_file is a file specification for the name of an object file.  If no file extension is specified, a file extension of "obj" is assumed if you are running a DOS, OS/2 or Windows NT-hosted version of the WATCOM Linker.  Also, if you are running a DOS, OS/2 or Windows NT-hosted version of the WATCOM Linker, the object file specification can contain wild cards (*, ?).  A file extension of "o" is assumed if you are running a QNX-hosted version of the WATCOM Linker. 

library_file is a file specification form the name of a library file.  Note that the file extension of the library file (usually "lib") must be specified; otherwise an object file will be assumed. 

obj_module is the name of an object module defined in an object or library file. 
Consider the following example. 
Example: 
   wlink form generic_os f \math\sin, mycos 
The WATCOM Linker is instructed to process the following object files: 
    
   \math\sin.obj 
   mycos.obj 
The object file "mycos.obj" is located in the current directory since no path was specified. 
More than one "FILE" directive may be used.  The following example is equivalent to the preceding one. 
Example: 
   wlink form generic_os f \math\sin f mycos 
Thus, other directives may be placed between lists of object files. 
The "FILE" directive can also specify object modules from a library file or object file.  Consider the following example. 
Example: 
   wlink form generic_os f \math\math.lib(sin) 
The WATCOM Linker is instructed to process the object module "sin" contained in the library file "math.lib" in the directory "\math". 
In the following example, the WATCOM Linker will process the object module "sin" contained in the object file "math.obj" in the directory "\math". 
Example: 
   wlink form generic_os f \math\math(sin) 
In the following example, the WATCOM Linker will include all object modules contained in the library file "math.lib" in the directory "\math". 
Example: 
   wlink form generic_os f \math\math.lib


### The FORMAT Directive

The "FORMAT" directive is used to specify the format of the executable file that the WATCOM Linker is to generate.  The format of the "FORMAT" directive (short form "FORM") is as follows. 
    
     FORMAT form 
     form ::= DOS [COM] 
           | WINDOWS [win_dll] [MEMORY] [FONT] 
           | WINDOWS NT [TNT] [dll_attrs] 
           | OS2 [os2_type] [dll_attrs | os2_attrs] 
           | PHARLAP [EXTENDED | REX] 
           | NOVELL [NLM | LAN | DSK | NAM] 'description' 
           | QNX [FLAT] 
           | ELF [DLL] 
     dll_attrs ::= DLL [INITGLOBAL | INITINSTANCE] 
              [TERMINSTANCE | TERMGLOBAL] 
     win_attrs ::= [win_dll] [MEMORY] [FONT] 
     win_dll ::= DLL [INITGLOBAL | INITINSTANCE] 
     os2_type ::= FLAT | LE | LX 
     os2_attrs ::= PM | PMCOMPATIBLE | FULLSCREEN 
               | PHYSDEVICE | VIRTDEVICE 

DOS (short form "D") tells the WATCOM Linker to generate a DOS "EXE" file.  For more information on DOS executable file formats, see the chapter entitled DOS:  The DOS Executable File Format. 

WINDOWS tells the WATCOM Linker to generate a Windows executable file.  For more information on Windows executable file formats, see the chapter entitled Windows:  The Windows Executable and DLL File Formats. 

WINDOWS NT tells the WATCOM Linker to generate a Windows NT executable file ("PE" format).  For more information on Windows NT executable file formats, see the chapter entitled NT:  The Windows NT Executable and DLL File Formats. 

OS2 tells the WATCOM Linker to generate an OS/2 executable file format.  For more information on OS/2 executable file formats, see the chapter entitled OS/2:  The OS/2 Executable and DLL File Formats. 

PHARLAP (short form "PHAR") tells the WATCOM Linker to generate an executable file that will run under Phar Lap's 386|DOS-Extender.  For more information on Phar Lap executable file formats, see the chapter entitled Phar Lap:  The Phar Lap Executable File Format. 

NOVELL (short form "NOV") tells the WATCOM Linker to generate a NetWare 386 executable file, more commonly called a NetWare Loadable Module (NLM).  For more information on NetWare 386 executable file formats, see the chapter entitled NetWare:  The NetWare 386 Executable File Format. 

QNX tells the WATCOM Linker to generate a QNX executable file.  For more information on QNX executable file formats, see the chapter entitled QNX:  The QNX Executable File Format. 

ELF tells the WATCOM Linker to generate an ELF format executable file. 
If no "FORMAT" directive is specified and you are running a DOS, OS/2 or Windows NT-hosted version of the WATCOM Linker, the executable file format will be selected in the following way. 

 1.If a reference to a dynamic link library is encountered, an OS/2 executable file will be generated. 

 2.If a 386 object module is encountered, an executable file that runs under Phar Lap's 386|DOS-Extender will be generated. 

 3.Otherwise, a DOS executable file will be generated. 
If no "FORMAT" directive is specified and you are running a QNX-hosted version of the WATCOM Linker, the executable file format will be selected in the following way. 

 1.If a reference to a dynamic link library is encountered, an OS/2 format executable file will be generated. 

 2.If a 386 object module is encountered, an executable file that runs under Phar Lap's 386|DOS-Extender will be generated. 

 3.Otherwise, a QNX executable file will be generated.


### The LANGUAGE Directive

The "LANGUAGE" directive is used to specify the language in which strings in the WATCOM Linker directives are specified.  The format of the "LANGUAGE" directive (short form "LANG") is as follows. 
    
     LANGUAGE lang 
     lang ::= JAPANESE | CHINESE | KOREAN 

JAPANESE (short form "JA") specifies that strings are to be handled as if they contained characters from the Japanese Double-Byte Character Set (DBCS). 

CHINESE (short form "CH") specifies that strings are to be handled as if they contained characters from the Chinese Double-Byte Character Set (DBCS). 

KOREAN (short form "KO") specifies that strings are to be handled as if they contained characters from the Korean Double-Byte Character Set (DBCS).


### The LIBRARY Directive

The "LIBRARY" directive is used to specify the library files to be searched when unresolved symbols remain after processing all specified input object files.  The format of the "LIBRARY" directive (short form "L") is as follows. 
    
     LIBRARY library_file{,library_file} 

library_file is a file specification for the name of a library file.  If no file extension is specified, a file extension of "lib" is assumed. 
Consider the following example. 
Example: 
   wlink form generic_os file trig lib \math\trig, \cmplx\trig 
The WATCOM Linker is instructed to process the following object file: 
    
   trig.obj 
If any unresolved symbol references remain after all object files have been processed, the following library files will be searched: 
    
   \math\trig.lib 
   \cmplx\trig.lib 
More than one "LIBRARY" directive may be used.  The following example is equivalent to the preceding one. 
Example: 
   wlink form generic_os f trig lib \math\trig lib \cmplx\trig 
Thus other directives may be placed between lists of library files.


#### Searching for Libraries Specified in Environment Variables

The "LIB" environment variable can be used to specify a list of paths that will be searched for library files.  The "LIB" environment variable can be set using the "set" command as follows: 
    
   set lib=\graphics\lib;\utility 
Consider the following "LIBRARY" directive and the above definition of the "LIB" environment variable. 
    
   library \mylibs\util, graph 
If undefined symbols remain after processing all object files specified in all "FILE" directives, the WATCOM Linker will resolve these references by searching the following libraries in the specified order. 

 1.the library file "\mylibs\util.lib" 

 2.the library file "graph.lib" in the current directory 

 3.the library file "\graphics\lib\graph.lib" 

 4.the library file "\utility\graph.lib" 
Notes: 

 1.If a library file specified in a "LIBRARY" directive contains an absolute path specification, the WATCOM Linker will not search any of the paths specified in the "LIB" environment string for the library file.  An absolute path specification is one that begins with a drive specification or the "\" character. 

 2.Once a library file has been found, no further elements of the "LIB" environment variable are searched for other libraries of the same name.  That is, if the library file "\graphics\lib\graph.lib" exists, the library file "\utility\graph.lib" will not be searched even though unresolved references may remain. 
Since the WATCOM Linker can generate various executable file formats, it may be necessary to specify a different set of libraries for each executable file format.  For this reason, the directories specified in the following environment variables will be searched. 

LIBDOS The directories specified in the "LIBDOS" environment variable will be searched if the WATCOM Linker is generating a DOS executable file. 

LIBOS2 The directories specified in the "LIBOS2" environment variable will be searched if the WATCOM Linker is generating an OS/2 executable file. 

LIBOS2FLAT The directories specified in the "LIBOS2FLAT" environment variable will be searched if the WATCOM Linker is generating an OS/2 flat executable file. 

LIBPHAR The directories specified in the "LIBPHAR" environment variable will be searched if the WATCOM Linker is generating a Phar Lap executable file. 

LIBNOV The directories specified in the "LIBNOV" environment variable will be searched if the WATCOM Linker is generating a NetWare 386 executable file. 

LIBQNX The directories specified in the "LIBQNX" environment variable will be searched if the WATCOM Linker is generating a QNX executable file. 

LIBWIN The directories specified in the "LIBWIN" environment variable will be searched if the WATCOM Linker is generating a Windows executable file. 

LIB286 The directories specified in the "LIB286" environment variable will be searched if, after processing all object files, the WATCOM Linker has only detected 16-bit object files and the executable file format has not yet been determined. 

LIB386 The directories specified in the "LIB386" environment variable will be searched if, after processing all object files, the WATCOM Linker has detected a 32-bit object file and the executable file format has not yet been determined. 
Note that the directories specified in the above mentioned environment variables will be searched before the directories specified in the "LIB" environment variable.


#### Converting Libraries Created using Phar Lap 386|LIB

Phar Lap's librarian, 386|LIB, creates libraries whose dictionary is a different format from the one used by other librarians.  For this reason, linking an application using the WATCOM Linker with libraries created using 386|LIB will not work.  Library files created using 386|LIB must be converted to the form recognized by the WATCOM Linker.  This is achieved by issuing the following WLIB command. 
    
   wlib newlib +pharlib.lib 
The library file "pharlib.lib" is a library created using 386|LIB.  The library file "newlib.lib" will be created so that the WATCOM Linker can now process it.


### The LIBFILE Directive

The "LIBFILE" directive is used to specify the object files that the WATCOM Linker is to process.  The format of the "LIBFILE" directive (short form "LIBF") is as follows. 
    
     LIBFILE obj_file{,obj_file} 

obj_file is a file specification for the name of an object file.  If no file extension is specified, a file extension of "obj" is assumed if you are running a DOS, OS/2 or Windows NT-hosted version of the WATCOM Linker.  Also, if you are running a DOS, OS/2 or Windows NT-hosted version of the WATCOM Linker, the object file specification can contain wild cards (*, ?).  A file extension of "o" is assumed if you are running a QNX-hosted version of the WATCOM Linker. 
The difference between the "LIBFILE" directive and the "FILE" directive is as follows. 

 1.The "LIBFILE" directive only allows object files.  The "FILE" directive allows object files as well as a syntax for specifying object modules from library files and object files. 

 2.When searching for an object file specified in a "LIBFILE" directive, the default directory will be searched first, followed by the paths specified in the "LIBPATH" directive, and finally the paths specified in the appropriate "LIB" environment variable.  Note that if the object file name contains a path, only the specified path will be searched. 

 3.Object files specified in a "LIBFILE" directive will not be used to create the name of the executable file when no "NAME" directive is specified. 
Essentially, object files that appear in "LIBFILE" directives are are viewed as components of a library that have not been explicitly placed in a library file. 
Consider the following linker directive file. 
    
   libpath \libs 
   libfile mystart 
   path \objs 
   file file1, file2 
The WATCOM Linker is instructed to process the following object files: 
    
   \libs\mystart.obj 
   \objs\file1.obj 
   \objs\file2.obj 
Note that the executable file will have file name "file1" and not "mystart".


### The LIBPATH Directive

The "LIBPATH" directive is used to specify the directories that are to be searched for library files appearing in subsequent "LIBRARY" directives and object files appearing in subsequent "LIBFILE" directives.  The format of the "LIBPATH" directive (short form "LIBP") is as follows. 
    
     LIBPATH [path_name{;path_name}] 

path_name is a path name. 
Consider a directive file containing the following linker directives. 
    
   file test 
   libpath \math 
   library trig 
   libfile newsin 
First, the WATCOM Linker will process the object file "test.obj" from the default directory.  The object file "newsin.obj" will then be processed, searching the default directory first.  If "newsin.obj" is not in the default directory, the "\math" directory will be searched.  If any unresolved references remain after processing the object files, the library file "trig.lib" will be searched.  If the file "trig.lib" does not exist in the default directory, the "\math" directory will be searched. 
It is also possible to specify a list of paths in a "LIBPATH" directive.  Consider the following example. 
    
   libpath \newmath;\math 
   library trig 
When processing undefined references, the WATCOM Linker will attempt to process the library file "trig.lib" in the default directory.  If "trig.lib" does not exist in the default directory, the "\newmath" directory will be searched.  If "trig.lib" does not exist in the "\newmath" directory, the "\math" directory will be searched. 
If the name of a library file appearing in a "LIBRARY" directive or the the name of an object file appearing in a "LIBFILE" directive contains a path specification, only the specified path will be searched. 
Note that 
    
   libpath path1 
   libpath path2 
is equivalent to the following. 
    
   libpath path2;path1


### The MODTRACE Directive

The "MODTRACE" directive instructs the WATCOM Linker to print a list of all modules that reference the symbols defined in the specified modules.  The format of the "MODTRACE" directive (short form "MODT") is as follows. 
    
     MODTRACE  module_name{,module_name} 

module_name is the name of an object module defined in an object or library file. 
The information is displayed in the map file.  Consider the following example. 
Example: 
   wlink form generic_os op map file test lib math modt trig 
If the module "trig" defines the symbols "sin" and "cos", the WATCOM Linker will list, in the map file, all modules that reference the symbols "sin" and "cos". 
Note: 

 1.The "MODTRACE" directive cannot be used in conjunction with the "VERBOSE" option.


### The NAME Directive

The "NAME" directive is used to provide a name for the executable file generated by the WATCOM Linker.  The format of the "NAME" directive (short form "N") is as follows. 
    
     NAME exe_file 

exe_file is a file specification for the name of the executable file.  If no file extension is specified, a file extension of "exe" is assumed unless the "FORMAT" directive is used to change the executable file format. 
Consider the following example. 
Example: 
   wlink form generic_os name myprog file test, test2, test3 
The WATCOM Linker is instructed to generate an executable file called "myprog.exe". 
Notes: 

 1.No file extension was given when the executable file name was specified.  The WATCOM Linker assumes a file extension that depends on the format of the executable file being generated.  The section entitled The FORMAT Directive describes the "FORMAT" directive and how the file extension is chosen for each executable file format. 

 2.If no "NAME" directive is present, the executable file will have the file name of the first object file processed by the WATCOM Linker.  If the first object file processed is called "test.obj" and no "NAME" directive is specified, an executable file called "test.exe" will be generated.


### The NEWSEGMENT Directive

By default, the WATCOM Linker automatically groups logical code segments into physical segments.  The "PACKCODE" option can be used to specify the size of the physical segments.  Note that all physical segments are the same size. 
The "NEWSEGMENT" directive provides an alternate method of grouping code segments into physical segments.  By placing this directive after a sequence of "FILE" directives, all code segments appearing in object modules specified by the sequence of "FILE" directives will be packed into a physical segment.  Note that the size of a physical segment may vary in size.  The format of the "NEWSEGMENT" directive (short form "NEW") is as follows. 
    
     NEWSEGMENT 
Consider the following example. 
    
   file file1, file2, file3 
   newsegment 
   file file4 
   file file5 
Code segments from file1, file2 and file3 will be grouped into one physical segment.  Code segments from file4 and file5 will be grouped into another physical segment. 
Note that code segments extracted from library files will be grouped into physical segments as well.  The size of these physical segments is determined by the "PACKCODE" option and is 64k by default.


### The OPTION Directive

The "OPTION" directive is used to specify options to the WATCOM Linker.  Some of the available options are specific to an executable file format.  A number of them, however, are common to any executable format.  We present the common options in this chapter.  For other options available with the format of executable that you are interested in creating, see the appropriate chapter.


#### The ARTIFICIAL Option

The "ARTIFICIAL" option should only be used if you are developing a WATCOM C++ application.  A WATCOM C++ application contains many compiler-generated symbols.  By default, the linker does not include these symbols in the map file.  The "ARTIFICIAL" option can be used if you wish to include these compiler-generated symbols in the map file. 
The format of the "ARTIFICIAL" option (short form "ART") is as follows. 
    
     OPTION ARTIFICIAL


#### The CACHE Option

The "CACHE" and "NOCACHE" options can be used to control caching of object files in memory by the linker.  The "CACHE" option enables the caching of object files while the "NOCACHE" option disables it. 
The format of the "CACHE" option (short form "CAC") is as follows. 
    
     OPTION CACHE 
The format of the "NOCACHE" option (short form "NOCAC") is as follows. 
    
     OPTION NOCACHE 
By default, the caching of object files is performed by the following versions of the linker.  The "NOCACHE" option can be used to disable the caching of object files by these versions. 

 1.OS/2 1.x-hosted version 

 2.DOS-hosted version (including 32-bit protected-mode version) 

 3.QNX-hosted version 
By default, the caching of object files is not performed by the following versions of the linker.  The "CACHE" option can be used to enable the caching of object files by these versions. 

 1.OS/2 2.x-hosted version 

 2.Windows NT-hosted version 
When linking large applications with many object files, caching object files will cause extensive use of memory by the linker.  On virtual memory systems such as OS/2 and Windows NT, this can cause extensive page file activity when real memory resources have been exhausted.  This can degrade the performance of other tasks on your system.  For this reason, the OS/2 and Windows NT-hosted versions of the linker do not perform object file caching by default.  This does not imply that object file caching is not beneficial.  If your system has lots of real memory or the linker is running as the only task on the machine, object file caching can certainly improve the performance of the linker. 
On single-tasking environments such as DOS, the benefits of improved linker performance outweighs the memory demands associated with object file caching.  For this reason, object file caching is performed by default on these systems.  If the memory requirements of the linker exceed the amount of memory on your system, the "NOCACHE" option can be specified. 
The QNX operating system is a multi-tasking real-time operating system.  However, it is not a virtual memory system.  Caching object files can consume large amounts of memory.  This may prevent other tasks on the system from running, a problem that may be solved by using the "NOCACHE" option.


#### The CASEEXACT Option

The "CASEEXACT" option tells the WATCOM Linker to respect case when resolving references to global symbols.  That is, "ScanName" and "SCANNAME" represent two different symbols.  By default, the WATCOM Linker is case insensitive; "ScanName" and "SCANNAME" represent the same symbol.  The format of the "CASEEXACT" option (short form "C") is as follows. 
    
     OPTION CASEEXACT 
If you have specified the "CASEEXACT" option in the default directive files WLINK.LNK or WLSYSTEM.LNK, it is possible to override this option by using the "NOCASEEXACT" option.  The "NOCASEEXACT" option turns off case-sensitive linking.  The format of the "NOCASEEXACT" option (short form "NOC") is as follows. 
    
     OPTION NOCASEEXACT 
The file WLINK.LNK is a special linker directive file that is automatically processed by the WATCOM Linker before processing any other directives.  On a DOS, OS/2 or Windows NT-hosted system, this file should be located in one of the paths specified in the PATH environment variable.  On a QNX-hosted system, this file should be located in the /etc directory.  A default version of this file is located in the \WATCOM\BIN directory on DOS-hosted systems, the \WATCOM\BINP directory on OS/2-hosted systems, the /etc directory on QNX-hosted systems, and the \WATCOM\BINNT directory on Windows NT-hosted systems.  Note that the file WLINK.LNK includes the file WLSYSTEM.LNK which is located in the \WATCOM\BINB directory on DOS, OS/2 and Windows NT-hosted systems and the /etc directory on QNX-hosted systems. 
The files WLINK.LNK and WLSYSTEM.LNK reference the WATCOM environment variable which must be set to the directory in which you installed your software.


#### The DOSSEG Option

The "DOSSEG" option tells the WATCOM Linker to order segments in a special way.  The format of the "DOSSEG" option (short form "D") is as follows. 
    
     OPTION DOSSEG 
When the "DOSSEG" option is specified, segments will be ordered in the following way. 

 1.all segments not belonging to group "DGROUP" with class "CODE" 

 2.all other segments not belonging to group "DGROUP" 

 3.all segments belonging to group "DGROUP" with class "BEGDATA" 

 4.all segments belonging to group "DGROUP" not with class "BEGDATA", "BSS" or "STACK" 

 5.all segments belonging to group "DGROUP" with class "BSS" 

 6.all segments belonging to group "DGROUP" with class "STACK" 
A special segment belonging to class "BEGDATA" is defined when linking with WATCOM run-time libraries.  This segment is initialized with the hexadecimal byte pattern "01" and is the first segment in group "DGROUP" so that storing data at location 0 can be detected. 
Segments belonging to class "BSS" contain uninitialized data.  Note that this only includes uninitialized data in segments belonging to group "DGROUP".  Segments belonging to class "STACK" are used to define the size of the stack used for your application.  Segments belonging to the classes "BSS" and "STACK" are last in the segment ordering so that uninitialized data need not take space in the executable file. 
When using WATCOM run-time libraries, it is not necessary to specify the "DOSSEG" option.  One of the object files in the WATCOM run-time libraries contains a special record that specifies the "DOSSEG" option. 
If no "DOSSEG" option is specified, segments are ordered in the order they are encountered by the WATCOM Linker. 
When the "DOSSEG" option is specified, the WATCOM Linker defines two special variables.  _edata defines the start of the "BSS" class of segments and _end defines the end of the "BSS" class of segments.  Your program must not redefine these symbols.


#### The ELIMINATE Option

The "ELIMINATE" option can be used to enable dead code elimination.  Dead code elimination is a process the linker uses to remove unreferenced segments from the application.  The linker will only remove segments that contain code; unreferenced data segments will not be removed. 
The format of the "ELIMINATE" option (short form "EL") is as follows. 
    
     OPTION ELIMINATE 

Linking C/C++ Applications Typically, a module of C/C++ code contains a number of functions.  When this module is compiled, all functions will be placed in the same code segment.  The chances of each function in the module being unreferenced are remote and the usefulness of the "ELIMINATE" option is greatly reduced. 
In order to maximize the effect of the "ELIMINATE" option, the "zm" compiler option is available to tell the WATCOM C/C++ compiler to place each function in its own code segment.  This allows the linker to remove unreferenced functions from modules that contain many functions. 
Note, that if a function is referenced by data, as in a jump table, the linker will not be able to eliminate the code for the function even if the data that references it is unreferenced. 
The WATCOM FORTRAN 77 compiler always places each function and subroutine in in its own code segment, even if they are contained in the same module.  Therefore when linking with the "ELIMINATE" option the linker will be able to eliminate code on a function/subroutine basis.


#### The MANGLEDNAMES Option

The "MANGLEDNAMES" option should only be used if you are developing a WATCOM C++ application.  Due to the nature of C++, the WATCOM C++ compiler generates mangled names for symbols.  A mangled name for a symbol includes the following. 

 1.symbol name 

 2.scoping information 

 3.typing information 
This information is stored in a cryptic form with the symbol.  When the linker encounters a mangled name in an object file, it formats the above information and produces this name in the map file. 
If you would like the linker to produce the mangled name as it appeared in the object file, specify the "MANGLEDNAMES" option. 
The format of the "MANGLEDNAMES" option (short form "MANG") is as follows. 
    
     OPTION MANGLEDNAMES


#### The MAP Option

The "MAP" option controls the generation of a map file.  The format of the "MAP" option (short form "M") is as follows. 
    
     OPTION MAP[=map_file] 

map_file is a file specification for the name of the map file.  If no file extension is specified, a file extension of "map" is assumed. 
By default, no map file is generated.  Specifying this option causes the WATCOM Linker to generate a map file.  The map file is simply a memory map of your program.  That is, it specifies the relative location of all global symbols in your program.  The map file also contains the size of your program. 
If no file name is specified, the map file will have a default file extension of "map" and the same file name as the executable file.  Note that the map file will be created in the current directory even if the executable file name specified in the "NAME" directive contains a path specification. 
Alternatively, a file name can be specified.  The following directive instructs the WATCOM Linker to generate a map file and call it "myprog.map" regardless of the name of the executable file. 
    
   option map=myprog 
You can also specify a path and/or file extension when using the "MAP=" form of the "MAP" option.


#### The MAXERRORS Option

The "MAXERRORS" option can be used to set a limit on the number of error messages generated by the linker.  Note that this does not include warning messages.  When this limit is reached, the linker will issue a fatal error and terminate. 
The format of the "MAXERRORS" option (short form "MAXE") is as follows. 
    
     OPTION MAXERRORS=n 

n is the maximum number of error messages issued by the linker.


#### The NAMELEN Option

The "NAMELEN" option tells the WATCOM Linker that all symbols must be uniquely identified in the number of characters specified or less.  If any symbol fails to satisfy this condition, a warning message will be issued.  The warning message will state that a symbol has been defined more than once. 
The format of the "NAMELEN" option (short form "NAMEL") is as follows. 
    
     OPTION NAMELEN=n 

n represents a value.  The complete form of n is the following. 
    
   [0x]d{d}[k|m] 
d represents a decimal digit.  If 0x is specified, the string of digits represents a hexadecimal number.  If k is specified, the value is multiplied by 1024.  If m is specified, the value is multiplied by 1024*1024. 
Some computer systems, for example, require that all global symbols be uniquely identified in 8 characters.  By specifying an appropriate value for the "NAMELEN" option, you can ease the task of porting your application to other computer systems.


#### The NODEFAULTLIBS Option

Special object module records that specify default libraries are placed in object files generated by WATCOM compilers.  These libraries reflect the memory and floating-point model that a source file was compiled for and are automatically searched by the WATCOM Linker when unresolved symbols are detected.  These libraries are assumed to exist in the current directory or in one of the paths specified in the "LIBGENERIC_OS" and "LIB" environment variables.  By simply including the directories containing the libraries required to link your application in one of these environment variables, you need not specify any libraries in your linker directive files. 
Note that all library files that appear in a "LIBRARY" directive are searched before default libraries.  The "NODEFAULTLIBS" option instructs the WATCOM Linker to ignore default libraries.  That is, only libraries appearing in a "LIBRARY" directive are searched. 
The format of the "NODefaultlibs" option (short form "NOD") is as follows. 
    
     OPTION NODEFAULTLIBS


#### The OSNAME Option

The "OSNAME" option can be used to set the name of the target operating system of the executable file generated by the linker.  The format of the "OSNAME" option (short form "OSN") is as follows. 
    
     OPTION OSNAME='string' 

string is any sequence of characters. 
The information specified by the "OSNAME" option will be displayed in the creating a ?  executable message.  This is the last line of output produced by the linker, provided the "QUIET" option is not specified.  Consider the following example. 
    
   option osname='SuperOS' 
The last line of output produced by the linker will be as follows. 
    
   creating a SuperOS executable


#### The PACKCODE Option

By default, the WATCOM Linker automatically groups logical code segments into physical segments.  The "PACKCODE" option is used to specify the size of the physical segment.  The format of the "PACKCODE" option (short form "PAC") is as follows. 
    
     OPTION PACKCODE=n 

n represents a value.  The complete form of n is the following. 
    
   [0x]d{d}[k|m] 
d represents a decimal digit.  If 0x is specified, the string of digits represents a hexadecimal number.  If k is specified, the value is multiplied by 1024.  If m is specified, the value is multiplied by 1024*1024. 
n specifies the size of the physical segments into which code segments are packed.  The default value of n is 64K for 16-bit applications and 4G for 32-bit applications.  Note that this is also the maximum size of a physical segment.  To suppress automatic grouping of code segments, specify a value of 0 for n. 
Notes: 

 1.Only adjacent segments are packed into a physical segment. 

 2.Segments belonging to the same group are packed in a physical segment.  Segments belonging to different groups are not packed into a physical segment. 

 3.Segments with different attributes are not packed together unless they are explicitly grouped.


#### The QUIET Option

The "QUIET" option tells the WATCOM Linker to suppress all informational messages.  Only warning, error and fatal messages will be issued.  By default, the WATCOM Linker issues informational messages.  The format of the "QUIET" option (short form "Q") is as follows. 
    
     OPTION QUIET


#### The REDEFSOK Option

The "REDEFSOK" option tells the WATCOM Linker to ignore redefined symbols and to generate an executable file anyway.  By default, warning messages are displayed and an executable file is generated if redefined symbols are present. 
The format of the "REDEFSOK" option (short form "RED") is as follows. 
    
     OPTION REDEFSOK 
The "NOREDEFS" option tells the WATCOM Linker to treat redefined symbols as an error and to not generate an executable file.  By default, warning messages are displayed and an executable file is generated if redefined symbols are present. 
The format of the "NOREDEFS" option (short form "NORED") is as follows. 
    
     OPTION NOREDEFS


#### The STACK Option

The "STACK" option can be used to increase the size of the stack.  The format of the "STACK" option (short form "ST") is as follows. 
    
     OPTION STACK=n 

n represents a value.  The complete form of n is the following. 
    
   [0x]d{d}[k|m] 
d represents a decimal digit.  If 0x is specified, the string of digits represents a hexadecimal number.  If k is specified, the value is multiplied by 1024.  If m is specified, the value is multiplied by 1024*1024. 
The default stack size is 4096 bytes for protected-mode 32-bit applications.  Otherwise the default stack size is 2048 bytes.  During execution of your program, you may get an error message indicating your stack has overflowed.  If you encounter such an error, you must link your application again, this time specifying a larger stack size using the "STACK" option. 
Example: 
   option stack=8192


#### The STATIC Option

The "STATIC" option should only be used if you are developing a WATCOM C or C++ application.  The WATCOM C and C++ compilers produce definitions for static symbols in the object file.  By default, these static symbols do not appear in the map file.  If you want static symbols to be displayed in the map file, use the "STATIC" option. 
The format of the "STATIC" option (short form "STAT") is as follows. 
    
     OPTION STATIC


#### The SYMFILE Option

The "SYMFILE" option provides a method for specifying an alternate file for debugging information.  The format of the "SYMFILE" option (short form "SYMF") is as follows. 
    
     OPTION SYMFILE[=symbol_file] 

symbol_file is a file specification for the name of the symbol file.  If no file extension is specified, a file extension of "sym" is assumed. 
By default, no symbol file is generated; debugging information is appended at the end of the executable file.  Specifying this option causes the WATCOM Linker to generate a symbol file.  The symbol file contains the debugging information generated by the WATCOM Linker when the "DEBUG" directive is used.  The symbol file can then be used by WATCOM Debugger.  If no debugging information is requested, no symbol file is created, regardless of the presence of the "SYMFILE" option. 
If no file name is specified, the symbol file will have a default file extension of "sym" and the same file name as the executable file.  Note that the symbol file will be created in the current directory even if the executable file name specified in the "NAME" directive contains a path specification. 
Alternatively, a file name can be specified.  The following directive instructs the WATCOM Linker to generate a symbol file and call it "myprog.sym" regardless of the name of the executable file. 
    
   option symf=myprog 
You can also specify a path and/or file extension when using the "SYMFILE=" form of the "SYMFILE" option. 
Note: 

 1.This option should be used to debug a DOS "COM" executable file.  A DOS "COM" executable file must not contain any additional information other than the executable information itself since DOS uses the size of the file to determine what to load. 

 2.This option should be used when creating a Microsoft Windows executable file.  Typically, before an executable file can be executed as a Microsoft Windows application, a resource compiler takes the Windows executable file and a resource file as input and combines them.  If the executable file contains debugging information, the resource compiler will strip the debugging information from the executable file.  Therefore, debugging information must not be part of the executable file created by the WATCOM Linker.


#### The UNDEFSOK Option

The "UNDEFSOK" option tells the WATCOM Linker to generate an executable file even if undefined symbols are present.  By default, no executable file will be generated if undefined symbols are present. 
The format of the "UNDEFSOK" option (short form "U") is as follows. 
    
     OPTION UNDEFSOK


#### The VERBOSE Option

The "VERBOSE" option controls the amount of information produced by the WATCOM Linker in the map file.  The format of the "VERBOSE" option (short form "V") is as follows. 
    
     OPTION VERBOSE 
If the "VERBOSE" option is specified, the WATCOM Linker will list, for each object file, all segments it defines and their sizes.  By default, this information is not produced in the map file. 
Note that the "VERBOSE" option cannot be used in conjunction with the "MODTRACE" or "SYMTRACE" directives.


### The PATH Directive

The "PATH" directive is used to specify the directories that are to be searched for object files appearing in subsequent "FILE" directives.  When the "PATH" directive is specified, the current directory will no longer be searched unless it appears in the "PATH" directive.  The format of the "PATH" directive (short form "P") is as follows. 
    
     PATH path_name{;path_name} 

path_name is a path name. 
Consider a directive file containing the following linker directives. 
    
   path \math 
   file sin 
   path \stats 
   file mean, variance 
It instructs the WATCOM Linker to process the following object files: 
    
   \math\sin.obj 
   \stats\mean.obj 
   \stats\variance.obj 
It is also possible to specify a list of paths in a "PATH" directive.  Consider the following example. 
    
   path \math;\stats 
   file sin 
First, the WATCOM Linker will attempt to load the file "\math\sin.obj".  If unsuccessful, the WATCOM Linker will attempt to load the file "\stats\sin.obj". 
It is possible to override the path specified in a "PATH" directive by preceding the object file name in a "FILE" directive with an absolute path specification.  An absolute path specification is one that begins with a drive specification or the "\" character. 
    
   path \math 
   file sin 
   path \stats 
   file mean, \mydir\variance 
The above directive file instructs the WATCOM Linker to process the following object files: 
    
   \math\sin.obj 
   \stats\mean.obj 
   \mydir\variance.obj


### The SYMTRACE Directive

The "SYMTRACE" directive instructs the WATCOM Linker to print a list of all modules that reference the specified symbols.  The format of the "SYMTRACE" directive (short form "SYMT") is as follows. 
    
     SYMTRACE  symbol_name{,symbol_name} 

symbol_name is the name of a symbol. 
The information is displayed in the map file.  Consider the following example. 
Example: 
   wlink form generic_os op map file test lib math symt sin, cos 
The WATCOM Linker will list, in the map file, all modules that reference the symbols "sin" and "cos". 
Note: 

 1.The "SYMTRACE" directive cannot be used in conjunction with the "VERBOSE" option.


### The SYSTEM Directive

There are two forms of the "SYSTEM" directive. 
The first form of the "SYSTEM" directive (short form "SYS") is called a system definition directive.  It allows you to associate a set of linker directives with a user-specified name called the system name.  This set of linker directives is called a system definition block.  The format of a system definition directive is as follows. 
    
     SYSTEM BEGIN system_name {directive} END 

system_name is a user-defined system name. 

directive is a linker directive. 
A system definition directive cannot be specified within another system definition directive. 
The second form of the "SYSTEM" directive is as follows. 
    
     SYSTEM system_name 

system_name is a user-defined system name. 
When this form of the "SYSTEM" directive is encountered, all directives specified in the system definition block identified by system_name will be processed. 
Let us consider an example that demonstrates the use of the "SYSTEM" directive.  The following linker directives define a system called statistics. 
    
   system begin statistics 
   form generic_os 
   libpath \libs 
   library stats, graphics 
   option stack=8k 
   end 
They specify that a statistics application is to be created by using the libraries "stats.lib" and "graphics.lib".  These library files are located in the directory "\libs".  The application requires a stack size of 8k and a GENERIC_OS executable will be generated. 
Suppose the linker directives in the above example are contained in the file "stats.lnk".  If we wish to create a statistics application, we can issue the following command. 
    
   wlink @stats system statistics file myappl 
As demonstrated by the above example, the "SYSTEM" directive can be used to localize the common attributes that describe a class of applications. 
For additional examples on the use of the "SYSTEM" directive, examine the contents of the file WLINK.LNK. 
The file WLINK.LNK is a special linker directive file that is automatically processed by the WATCOM Linker before processing any other directives.  On a DOS, OS/2 or Windows NT-hosted system, this file should be located in one of the paths specified in the PATH environment variable.  On a QNX-hosted system, this file should be located in the /etc directory.  A default version of this file is located in the \WATCOM\BIN directory on DOS-hosted systems, the \WATCOM\BINP directory on OS/2-hosted systems, the /etc directory on QNX-hosted systems, and the \WATCOM\BINNT directory on Windows NT-hosted systems.  Note that the file WLINK.LNK includes the file WLSYSTEM.LNK which is located in the \WATCOM\BINB directory on DOS, OS/2 and Windows NT-hosted systems and the /etc directory on QNX-hosted systems. 
The files WLINK.LNK and WLSYSTEM.LNK reference the WATCOM environment variable which must be set to the directory in which you installed your software.


#### Special System Names

There are two special system names.  When the linker has processed all object files and the executable file format has not been determined, and a system definition block has not been processed, the directives specified in the "286" or "386" system definition block will be processed.  The "386" system definition block will be processed if a 32-bit object file has been processed.  Furthermore, only a restricted set of linker directives is allowed in a "286" and "386" system definition block.  They are as follows. 

oFORMAT 
oLIBFILE 
oLIBPATH 
oLIBRARY 
oNAME 
oOPTION 
oRUNTIME (for Phar Lap executable files only) 
oSEGMENT (for OS/2 and QNX executable files only)


### The # Directive

The "#" directive is used to mark the start of a comment.  All text from the "#" character to the end of the line is considered a comment.  The format of the "#" directive is as follows. 
    
     # comment 

comment is any sequence of characters. 
The following directive file illustrates the use of comments. 
    
   file main, trigtest 
   # Use my own version of "sin" instead of the 
   # library version. 
   file mysin 
   library \math\trig


### The @ Directive

The "@" directive instructs the WATCOM Linker to process directives from an alternate source.  The format of the "@" directive is as follows. 
    
     @directive_var 
       or 
     @directive_file 

directive_var is the name of an environment variable.  The directives specified by the value of directive_var will be processed. 

directive_file is a file specification for the name of a linker directive file.  A file extension of "lnk" is assumed if no file extension is specified. 
The environment variable approach to specifying linker directives allows you to specify commonly used directives without having to specify them each time you invoke the WATCOM Linker.  If the environment variable "wlink" is set as in the following example, 
    
   set wlink=debug all option map, verbose library math 
   wlink @wlink 
each time the WATCOM Linker is invoked, full debugging information will be generated, a verbose map file will be created, and the library file "math.lib" will be searched for undefined references. 
A linker directive file is useful, for example, when the linker input consists of a large number of object files and you do not want to type their names on the command line each time you link your program.  Note that a linker directive file can also include other linker directive files. 
Let the file "memos.lnk" be a directive file containing the following lines. 
    
   form generic_os 
   name memos 
   file memos 
   file actions 
   file read 
   file msg 
   file prompt 
   file memmgr 
   library \termio\screen 
   library \termio\keyboard 
Consider the following example. 
Example: 
   wlink @memos 
The WATCOM Linker is instructed to process the contents of the directive file "memos.lnk".  The executable image file will be called "memos.exe".  The following object files will be loaded from the current directory. 
    
   memos.obj 
   actions.obj 
   read.obj 
   msg.obj 
   prompt.obj 
   memmgr.obj 
If any unresolved symbol references remain after all object files have been processed, the library files "screen.lib" and "keyboard.lib" in the directory "\termio" will be searched (in the order listed). 
Notes: 

 1.In the above example, we did not provide the file extension when the directive file was specified.  The WATCOM Linker assumes a file extension of "lnk" if none is present. 

 2.It is not necessary to list each object file and library with a separate directive.  The following linker directive file is equivalent. 
    
   form generic_os 
   name memos 
   file memos,actions,read,msg,prompt,memmgr 
   library \termio\screen,\termio\keyboard 
However, if you want to selectively specify what debugging information should be included, the first style of directive file will be easier to use.  This is illustrated in the following sample directive file. 
    
   form generic_os 
   name memos 
   debug lines 
   file memos 
   debug all 
   file actions 
   debug lines 
   file read 
   file msg 
   file prompt 
   file memmgr 
   debug 
   library \termio\screen 
   library \termio\keyboard 

 3.Information for a particular directive can span directive files.  This is illustrated in the following sample directive file. 
    
   form generic_os 
   file memos, actions, read, msg, prompt, memmgr 
   file @dbgfiles 
   library \termio\screen 
   library \termio\keyboard 
The directive file "dbgfiles.lnk" contains, for example, those object files that are used for debugging purposes.


## DOS:  The DOS Executable File Format

This chapter deals with those aspects of the WATCOM Linker required to generate DOS executable files.  The DOS executable file format will only run under the DOS operating system.


### DOS:  The WATCOM Linker Command Line

Input to the WATCOM Linker is specified on the command line.  The following notation is used to describe the syntax of WATCOM Linker commands. 

ABC All items in upper case are required. 

[abc] The item abc is optional. 

{abc} The item abc may be repeated zero or more times. 

{abc}+ The item abc may be repeated one or more times. 

a|b|c One of a, b or c may be specified. 

a ::= b The item a is defined in terms of b. 
The WATCOM Linker command line format is as follows. 
    
   WLINK {directive} 
where directive is any of the following: 

BEGIN {section_type [INTO ovl_file] {directive}} END 
   section_type ::= SECTION | AUTOSECTION 

| DEBUG [[WATCOM] db_list | CODEVIEW | DWARF] 
   db_list ::= [db_option{,db_option}] 
   db_option ::= LINES | TYPES | LOCALS | ALL 

| DISABLE msg_num{,msg_num} 

| FILE obj_spec{,obj_spec} 
   obj_spec ::= obj_file[(obj_module)] | library_file[(obj_module)] 

| FIXEDLIB library_file{,library_file} 

| FORMAT DOS [COM] 

| LIBFILE obj_file{,obj_file} 

| LIBPATH path_name{;path_name} 

| LIBRARY library_file{,library_file} 

| MODTRACE obj_module{,obj_module} 

| NAME exe_file 

| NEWSEGMENT 

| NOVECTOR symbol_name{,symbol_name} 

| OPTION option{,option} 
   option ::= AREA=n | ARTIFICIAL | [NO]CACHE | [NO]CASEEXACT 
           | DISTRIBUTE | DOSSEG | DYNAMIC | ELIMINATE 
           | MANGLEDNAMES | MAP[=map_file] | MAXERRORS=n 
           | NAMELEN=n | NODEFAULTLIBS | NOINDIRECT 
           | OSNAME='string' | PACKCODE=n | PACKDATA=n 
           | QUIET | REDEFSOK | SMALL | STACK=n 
           | STANDARD | STATIC | SYMFILE[=symbol_file] 
           | UNDEFSOK | VERBOSE 

| OVERLAY class{,class} 

| PATH path_name{;path_name} 

| SORT [GLOBAL] [ALPHABETICAL] 

| SYMTRACE symbol_name{,symbol_name} 

| SYSTEM BEGIN system_name {directive} END 

| SYSTEM system_name 

| VECTOR symbol_name{,symbol_name} 

| # comment 

| @ directive_file 

obj_file is a file specification for the name of an object file.  If no file extension is specified, a file extension of "obj" is assumed if you are running a DOS, OS/2 or Windows NT-hosted version of the WATCOM Linker.  Also, if you are running a DOS, OS/2 or Windows NT-hosted version of the WATCOM Linker, the object file specification can contain wild cards (*, ?).  A file extension of "o" is assumed if you are running a QNX-hosted version of the WATCOM Linker. 

library_file is a file specification for the name of a library file.  If library_file appears in a "LIBRARY" directive and no file extension is specified, a file extension of "lib" is assumed.  If library_file appears in a "FILE" directive and no file extension is specified, a file extension of "obj" is assumed if you are running a DOS, OS/2 or Windows NT-hosted version of the WATCOM Linker.  A file extension of "o" is assumed if you are running a QNX-hosted version of the WATCOM Linker. 
When a library file is specified in a "FILE" directive and obj_module is specified, the object module identified by obj_module is extracted from the library file and included in the executable file.  If obj_module is not specified (only the library file is specified), all object modules in the library are included in the executable file. 

obj_module is the name of an object module contained in a library file or object file. 
Object files may contain multiple object modules.  A simple way of creating such an object file is to concatenate a number of object files into a single object file.  Each of the original object files is now an object module in the resulting object file.  Also, some language processors may generate object files that contain multiple object modules.  Specifying obj_module allows you to select a particular object module from an object file. 

exe_file is a file specification for the name of the executable file.  If no file extension is specified, a file extension of "exe" is assumed unless a "COM" executable file is being generated in which case a file extension of "com" is assumed. 

ovl_file is a file specification for the name of an overlay file.  If no file extension is specified, a file extension of "ovl" is assumed. 

path_name is a path name. 

msg_num is a message number. 

directive_file is a file specification for the name of a linker directive file.  If no file extension is specified, a file extension of "lnk" is assumed. 

map_file is a file specification for the name of the map file.  If no file extension is specified, a file extension of "map" is assumed. 

symbol_file is a file specification for the name of the symbol file.  If no file extension is specified, a file extension of "sym" is assumed. 

symbol_name is the name of a symbol. 

system_name is the name of a system. 

comment is any sequence of characters. 

class is a segment class name. 

n represents a value.  The complete form of n is the following. 
    
   [0x]d{d}[k|m] 
d represents a decimal digit.  If 0x is specified, the string of digits represents a hexadecimal number.  If k is specified, the value is multiplied by 1024.  If m is specified, the value is multiplied by 1024*1024. 
You can view all the directives specific to DOS executable files by simply typing the following: 
    
   wlink ? dos 
Notes: 

 1.If the file "wlink.hlp" is located in one of the paths specified in the "PATH" environment variable, the contents of that file will be displayed when the following command is issued. 
    
   wlink ? 

 2.If all of the directive information does not fit on the command line, type the following. 
    
   wlink 
The prompt "WLINK>" will appear on the next line.  You can enter as many lines of directive information as required.  Press "Ctrl/Z" followed by the "Enter" key to terminate the input of directive information if you are running a DOS, OS/2 or Windows NT-hosted version of the WATCOM Linker.  Press "Ctrl/D" to terminate the input of directive information if you are running a QNX-hosted version of the WATCOM Linker.


### DOS:  WATCOM Linker Directives

Directives tell the WATCOM Linker how to create your program.  For example, using directives you can tell the WATCOM Linker which object files are to be included in the program, which library files to search to resolve undefined references, and the name of the executable file. 
The file WLINK.LNK is a special linker directive file that is automatically processed by the WATCOM Linker before processing any other directives.  On a DOS, OS/2 or Windows NT-hosted system, this file should be located in one of the paths specified in the PATH environment variable.  On a QNX-hosted system, this file should be located in the /etc directory.  A default version of this file is located in the \WATCOM\BIN directory on DOS-hosted systems, the \WATCOM\BINP directory on OS/2-hosted systems, the /etc directory on QNX-hosted systems, and the \WATCOM\BINNT directory on Windows NT-hosted systems.  Note that the file WLINK.LNK includes the file WLSYSTEM.LNK which is located in the \WATCOM\BINB directory on DOS, OS/2 and Windows NT-hosted systems and the /etc directory on QNX-hosted systems. 
The files WLINK.LNK and WLSYSTEM.LNK reference the WATCOM environment variable which must be set to the directory in which you installed your software. 
It is also possible to use environment variables when specifying a directive.  For example, if the LIBDIR environment variable is defined as follows, 
    
   set libdir=\test 
then the linker directive 
    
   library %libdir%\mylib 
is equivalent to the following linker directive. 
    
   library \test\mylib 
Note that a space must precede a reference to an environment variable. 
The following sections describe those WATCOM Linker directives that are used to generate DOS executable files.


#### DOS:  The AUTOSECTION Directive

The "AUTOSECTION" directive specifies that each object file that appears in a subsequent "FILE" directive, up to the next "SECTION" or "END" directive, will be assigned a different overlay.  The "AUTOSECTION" method of defining overlays is most useful when using the dynamic overlay manager, selected by specifying the "DYNAMIC" option.  For more information on the dynamic overlay manager, see the section entitled DOS:  Using Overlays. 
The format of the "AUTOSECTION" directive (short form "AUTOS") is as follows. 
    
     AUTOSECTION [INTO ovl_file] 

INTO specifies that all overlays are to be placed into a file, namely ovl_file.  If "INTO" (short form "IN") is not specified, the overlays are placed in the executable file. 

ovl_file is the file specification for the name of an overlay file.  If no file extension is specified, a file extension of "ovl" is assumed. 
Placing overlays in separate files has a number of advantages.  For example, if your application was linked into one file, it may not fit on a single diskette, making distribution of your application difficult.


#### DOS:  The BEGIN and END Directives

The "BEGIN" directive is used to define the start of an overlay area.  The "END" directive is used to define the end of an overlay area.  An overlay area is a piece of memory in which overlays are loaded.  All overlays defined between a "BEGIN" directive and the corresponding "END" directive are loaded into that overlay area. 
The format of the "BEGIN" directive (short form "B") is as follows. 
    
     BEGIN 
The format of the "END" directive (short form "E") is as follows. 
    
     END


#### DOS:  The FIXEDLIB Directive

The "FIXEDLIB" directive can be used to explicitly place the modules from a library file in the overlay section in which the "FIXEDLIB" directive appears.  The format of the "FIXEDLIB" directive (short form "FIX" ) is as follows. 
    
     FIXEDLIB library_file{,library_file} 

library_file is a file specification for the name of a library file.  If no file extension is specified, a file extension of "lib" is assumed. 
Consider the following example. 
    
   begin 
    section file1, file2 
    section file3 
    fixedlib mylib 
   end 
Two overlay sections are defined.  The first contains file1 and file2.  The second contains file3 and all modules contained in the library file "mylib.lib". 
Note that all modules extracted from library files that appear in a "LIBRARY" directive are placed in the root unless the "DISTRIBUTE" option is specified.  For more information on the "DISTRIBUTE" option, see the section entitled DOS:  The DISTRIBUTE Option.


#### DOS:  The FORCEVECTOR Directive

The "FORCEVECTOR" directive forces the WATCOM Linker to generate an overlay vector for the specified symbols.  The format of the "FORCEVECTOR" directive (short form "FORCEVE") is as follows. 
    
     FORCEVECTOR symbol_name{,symbol_name} 

symbol_name is a symbol name.


#### DOS:  The FORMAT Directive

The "FORMAT" directive is used to specify the format of the executable file that the WATCOM Linker is to generate.  The format of the "FORMAT" directive (short form "FORM") is as follows. 
    
     FORMAT form 
     form ::= DOS [COM] 
           | WINDOWS [win_dll] [MEMORY] [FONT] 
           | WINDOWS NT [TNT] [dll_attrs] 
           | OS2 [os2_type] [dll_attrs | os2_attrs] 
           | PHARLAP [EXTENDED | REX] 
           | NOVELL [NLM | LAN | DSK | NAM] 'description' 
           | QNX [FLAT] 
           | ELF [DLL] 
     dll_attrs ::= DLL [INITGLOBAL | INITINSTANCE] 
              [TERMINSTANCE | TERMGLOBAL] 
     win_attrs ::= [win_dll] [MEMORY] [FONT] 
     win_dll ::= DLL [INITGLOBAL | INITINSTANCE] 
     os2_type ::= FLAT | LE | LX 
     os2_attrs ::= PM | PMCOMPATIBLE | FULLSCREEN 
               | PHYSDEVICE | VIRTDEVICE 

DOS (short form "D") tells the WATCOM Linker to generate a DOS "EXE" file.  The name of the executable file will have extension "exe".  If "COM" is specified, a DOS "COM" file will be generated in which case the name of the executable file will have extension "com".  Note that these default extensions can be overridden by using the "NAME" directive to name the executable file. 
Not all programs can be generated in the "COM" format.  The following rules must be followed. 

 1.The program must consist of only one physical segment.  This implies that the size of the program (code and data) must be less than 64k. 

 2.The program must not contain any segment relocation.  A warning message will be issued by the WATCOM Linker each time a segment relocation is encountered. 
A DOS "COM" file cannot contain debugging information.  If you wish to debug a DOS "COM" file, you must use the "SYMFILE" option to instruct the WATCOM Linker to place the debugging information in a separate file. 

WINDOWS tells the WATCOM Linker to generate a Windows executable file.  For more information on Windows executable file formats, see the chapter entitled Windows:  The Windows Executable and DLL File Formats. 

WINDOWS NT tells the WATCOM Linker to generate a Windows NT executable file ("PE" format).  For more information on Windows NT executable file formats, see the chapter entitled NT:  The Windows NT Executable and DLL File Formats. 

OS2 tells the WATCOM Linker to generate an OS/2 executable file format.  For more information on OS/2 executable file formats, see the chapter entitled OS/2:  The OS/2 Executable and DLL File Formats. 

PHARLAP (short form "PHAR") tells the WATCOM Linker to generate an executable file that will run under Phar Lap's 386|DOS-Extender.  For more information on Phar Lap executable file formats, see the chapter entitled Phar Lap:  The Phar Lap Executable File Format. 

NOVELL (short form "NOV") tells the WATCOM Linker to generate a NetWare 386 executable file, more commonly called a NetWare Loadable Module (NLM).  For more information on NetWare 386 executable file formats, see the chapter entitled NetWare:  The NetWare 386 Executable File Format. 

QNX tells the WATCOM Linker to generate a QNX executable file.  For more information on QNX executable file formats, see the chapter entitled QNX:  The QNX Executable File Format. 

ELF tells the WATCOM Linker to generate an ELF format executable file. 
If no "FORMAT" directive is specified and you are running a DOS, OS/2 or Windows NT-hosted version of the WATCOM Linker, the executable file format will be selected in the following way. 

 1.If a reference to a dynamic link library is encountered, an OS/2 executable file will be generated. 

 2.If a 386 object module is encountered, an executable file that runs under Phar Lap's 386|DOS-Extender will be generated. 

 3.Otherwise, a DOS executable file will be generated. 
If no "FORMAT" directive is specified and you are running a QNX-hosted version of the WATCOM Linker, the executable file format will be selected in the following way. 

 1.If a reference to a dynamic link library is encountered, an OS/2 format executable file will be generated. 

 2.If a 386 object module is encountered, an executable file that runs under Phar Lap's 386|DOS-Extender will be generated. 

 3.Otherwise, a QNX executable file will be generated.


#### DOS:  The NOVECTOR Directive

The "NOVECTOR" directive forces the WATCOM Linker to not generate an overlay vector for the specified symbols.  The format of the "NOVECTOR" directive (short form "NOV") is as follows. 
    
     NOVECTOR symbol_name{,symbol_name} 

symbol_name is a symbol name. 
The WATCOM Linker will create an overlay vector in the following cases. 

 1.If a function in section A calls a function in section B and section B is not an ancestor of section A, an overlay vector will be generated for the function in section B.  See the section entitled DOS:  Using Overlays for a description of ancestor. 

 2.If a global symbol's address is referenced (except by a direct call) and that symbol is defined in an overlay section, an overlay vector for that symbol will be generated. 
Note that in the latter case, more overlay vectors may be generated that necessary.  Suppose section A contains three global functions, f, g and h.  Function f passes the address of function g to function h who can then calls function g indirectly.  Also, suppose function g is only called from sections that are ancestors of section A.  The WATCOM Linker will generate an overlay vector for function g even though none is required.  In such a case, the "NOVECTOR" directive can be used to remove the overhead associated with calling a function through an overlay vector.


#### DOS:  The OPTION Directive

The "OPTION" directive is used to specify options to the WATCOM Linker.  The format of the "OPTION" directive (short form "OP") is as follows. 
    
     OPTION option{,option} 
     option ::= AREA=n | ARTIFICIAL | [NO]CACHE | [NO]CASEEXACT 
             | DISTRIBUTE | DOSSEG | DYNAMIC | ELIMINATE 
             | MANGLEDNAMES | MAP[=map_file] | MAXERRORS=n 
             | NAMELEN=n | NODEFAULTLIBS | NOINDIRECT 
             | OSNAME='string' | PACKCODE=n | PACKDATA=n 
             | QUIET | REDEFSOK | SMALL | STACK=n 
             | STANDARD | STATIC | SYMFILE[=symbol_file] 
             | UNDEFSOK | VERBOSE 

map_file is a file specification for the name of the map file.  If no file extension is specified, a file extension of "map" is assumed. 

n represents a value.  The complete form of n is the following. 
    
   [0x]d{d}[k|m] 
d represents a decimal digit.  If 0x is specified, the string of digits represents a hexadecimal number.  If k is specified, the value is multiplied by 1024.  If m is specified, the value is multiplied by 1024*1024. 
The following sections describe the WATCOM Linker options specific to this executable format.  The options common to all executable formats are described in the chapter entitled General Directives and Options.


##### DOS:  The AREA Option

The "AREA" option can be used to set the size of the memory pool in which overlay sections are loaded by the dynamic overlay manager.  The format of the "AREA" option (short form "AR") is as follows. 
    
     OPTION AREA=n 

n represents a value.  The complete form of n is the following. 
    
   [0x]d{d}[k|m] 
d represents a decimal digit.  If 0x is specified, the string of digits represents a hexadecimal number.  If k is specified, the value is multiplied by 1024.  If m is specified, the value is multiplied by 1024*1024. 
The default size of the memory pool for a given application is selected by the WATCOM Linker and is equal to twice the size of the largest overlay. 
It is also possible to add to the memory pool at run-time.  If you wish to add to the memory pool at run-time, see the section entitled DOS:  Increasing the Dynamic Overlay Area.


##### DOS:  The DISTRIBUTE Option

The "DISTRIBUTE" option specifies that object modules extracted from library files are to be distributed throughout the overlay structure.  The format of the "DISTRIBUTE" option (short form "DIS") is as follows. 
    
     OPTION DISTRIBUTE 
An object module extracted from a library file will be placed in the overlay section that satisfies the following conditions. 

 1.The symbols defined in the object module are not referenced by an ancestor of the overlay section selected to contain the object module. 

 2.At least one symbol in the object module is referenced by an immediate descendant of the overlay section selected to contain the module. 
Note that libraries specified in the "FIXEDLIB" directive will not be distributed.  Also, if a symbol defined in a library module is referenced indirectly (its address is taken), the module extracted from the library will be placed in the root unless the "NOINDIRECT" option is specified.  For more information on the "NOINDIRECT" option, see the section entitled DOS:  The NOINDIRECT Option. 
For more information on overlays, see the section entitled DOS:  Using Overlays.


##### DOS:  The DYNAMIC Option

The "DYNAMIC" option tells the WATCOM Linker to use the dynamic overlay manager.  The format of the "DYNAMIC" option (short form "DY") is as follows. 
    
     OPTION DYNAMIC 
Note that the dynamic overlay manager can only be used with applications that have been compiled using the "of" option and a big code memory model.  The "of" option generates a special prologue/epilogue sequence for procedures that is required by the dynamic overlay manager.  See the compiler's User's Guide for more information on the "of" option. 
For more information on the dynamic overlay manager, see the section entitled DOS:  Using Overlays.


##### DOS:  The NOINDIRECT Option

The "NOINDIRECT" option suppresses the generation of overlay vectors for symbols that are referenced indirectly (their address is taken) when the module containing the symbol is not an ancestor of at least one module that indirectly references the symbol.  This can greatly reduce the number of overlay vectors and is a safe optimization provided there are no indirect calls to these symbols.  If, for example, the set of symbols that are called indirectly is known, you can use the "VECTOR" option to force overlay vectors for these symbols. 
The format of the "NOINDIRECT" option (short form "NOI") is as follows. 
    
     OPTION NOINDIRECT 
For more information on overlays, see the section entitled DOS:  Using Overlays.


##### DOS:  The PACKDATA Option

By default, the WATCOM Linker automatically groups logical code segments into physical segments.  The "PACKDATA" option is used to specify the size of the physical segment.  The format of the "PACKCODE" option (short form "PACKD") is as follows. 
    
     OPTION PACKDATA=n 

n represents a value.  The complete form of n is the following. 
    
   [0x]d{d}[k|m] 
d represents a decimal digit.  If 0x is specified, the string of digits represents a hexadecimal number.  If k is specified, the value is multiplied by 1024.  If m is specified, the value is multiplied by 1024*1024. 
n specifies the size of the physical segments into which far data segments are packed.  The default value of n is 64K.  Note that this is also the maximum size of a physical segment.  To suppress automatic grouping of far data segments, specify a value of 0 for n. 
Notes: 

 1.Only adjacent segments are packed into a physical segment. 

 2.Segments belonging to the same group are packed in a physical segment.  Segments belonging to different groups are not packed into a physical segment. 

 3.Segments with different attributes are not packed together unless they are explicitly grouped.


##### DOS:  The SMALL Option

The "SMALL" option tells the WATCOM Linker to use the standard overlay manager (as opposed to the dynamic overlay manager) and that near calls can be generated to overlay vectors corresponding to routines defined in the overlayed portion of your program.  The format of the "SMALL" option (short form "SM") is as follows. 
    
     OPTION SMALL 
This option should only be specified in the following circumstances. 

 1.Your program has been compiled for a small code memory model. 

 2.You are creating an overlayed application. 

 3.The code in your program, including overlay areas, does not exceed 64K. 
If the "SMALL" option is not specified and you are creating an overlayed application, the WATCOM Linker will generate far calls to overlay vectors.  In this case, your application must have been compiled using a big code memory model.


##### DOS:  The STANDARD Option

The "STANDARD" option instructs the WATCOM Linker to use the standard overlay manager (as opposed to the dynamic overlay manager).  Your application must be compiled for a big code memory model.  The format of the "STANDARD" option (short form "ST") is as follows. 
    
     OPTION STANDARD 
The standard overlay manager is the default.  For more information on overlays, see the section entitled DOS:  Using Overlays.


#### DOS:  The OVERLAY Directive

The "OVERLAY" directive allows you to specify the class of segments which are to be overlayed.  The format of the "OVERLAY" directive (short form "OV") is as follows. 
    
     OVERLAY class{,class} 

class is the class name of the segments to be overlayed. 
The "FILE" directive is used to specify the object files that belong to the overlay structure.  Each object file defines segments that contain code or data.  Segments are assigned a class name by the compiler.  A class is essentially a collection of segments with common attributes.  For example, compilers assign class names to segments so that segments containing code belong to one class(es) and segments containing data belong to another class(es).  When an overlay structure is defined, only segments belonging to certain classes are allowed in the overlay structure.  By default, the WATCOM Linker overlays all segments whose class name ends with "CODE".  These segments usually contain the executable code for a program. 
It is also possible to overlay other classes.  This is done using the "OVERLAY" directive.  For example, 
    
   overlay code, far_data 
places all segments belonging to the classes "CODE" and "FAR_DATA" in the overlay structure.  Segments belonging to the class "FAR_DATA" contain only data.  The above "OVERLAY" directive causes code and data to be overlayed. Therefore, for any module that contains segments in both classes, data in segments with class "FAR_DATA" will be in memory only when code in segments with class "CODE" are in memory.  This results in a more efficient use of memory.  Of course the data must be referenced only by code in the overlay and it must not be modified. 
 WARNING!  Care must be taken when overlaying data.  If a routine modifies data in an overlayed data segment, it should not assume it contains that value if it is invoked again.  The data may have been overwritten by another overlay. 
Notes: 

 1.You should not specify a class in an "OVERLAY" directive that belongs to the group "DGROUP".  These classes are "BEGDATA", "DATA", "BSS" and "STACK". 
If you are linking object files generated by a compiler that uses a class name that does not end with "CODE" for segments containing executable code, the "OVERLAY" directive can be used to identify the classes that belong to the overlay structure.  Consider the following example. 
Example: 
   overlay code1, code2 
Any segment belonging to the class called "CODE1" or "CODE2" is placed in the overlay structure.  Segments belonging to a class whose name ends with "CODE" will no longer be placed in the overlay structure.


#### DOS:  The SECTION Directive

The "SECTION" directive is used to define the start of an overlay.  All object files in subsequent "FILE" directives, up to the next "SECTION" or "END" directive, belong to that overlay.  The format of the "SECTION" directive (short form "S") is as follows. 
    
     SECTION [INTO ovl_file] 

INTO specifies that the overlay is to be placed into a separate file, namely ovl_file.  If "INTO" (short form "IN") is not specified, the overlay is placed in the executable file.  Note that more than one overlay can be placed in the same file by specifying the same file name in multiple "SECTION" directives. 

ovl_file is the file specification for the name of an overlay file.  If no file extension is specified, a file extension of "ovl" is assumed. 
Placing overlays in separate files has a number of advantages.  For example, if your application was linked into one file, it may not fit on a single diskette, making distribution of your application difficult.


#### DOS:  The VECTOR Directive

The "VECTOR" directive forces the WATCOM Linker to generate an overlay vector for the specified symbols and is intended to be used when the "NOINDIRECT" option is specified.  See the section entitled DOS:  The NOINDIRECT Option for additional information on the usage of the "VECTOR" directive. 
The format of the "VECTOR" directive (short form "VE") is as follows. 
    
     VECTOR symbol_name{,symbol_name} 

symbol_name is a symbol name. 
For more information on overlays, see the section entitled DOS:  Using Overlays.


### DOS:  Memory Layout

The following describes the segment ordering of an application linked by the WATCOM Linker.  Note that this assumes that the "DOSSEG" linker option has been specified. 

 1.all segments not belonging to group "DGROUP" with class "CODE" 

 2.all other segments not belonging to group "DGROUP" 

 3.all segments belonging to group "DGROUP" with class "BEGDATA" 

 4.all segments belonging to group "DGROUP" not with class "BEGDATA", "BSS" or "STACK" 

 5.all segments belonging to group "DGROUP" with class "BSS" 

 6.all segments belonging to group "DGROUP" with class "STACK" 
A special segment belonging to class "BEGDATA" is defined when linking with WATCOM run-time libraries.  This segment is initialized with the hexadecimal byte pattern "01" and is the first segment in group "DGROUP" so that storing data at location 0 can be detected. 
Segments belonging to class "BSS" contain uninitialized data.  Note that this only includes uninitialized data in segments belonging to group "DGROUP".  Segments belonging to class "STACK" are used to define the size of the stack used for your application.  Segments belonging to the classes "BSS" and "STACK" are last in the segment ordering so that uninitialized data need not take space in the executable file.


### DOS:  The WATCOM Linker Memory Requirements

The WATCOM Linker uses all available memory when linking an application.  For DOS-hosted versions of the WATCOM Linker, this includes expanded memory (EMS) and extended memory.  It is possible for the size of the image being linked to exceed the amount of memory available in your machine, particularly if the image file is to contain debugging information. For this reason, a temporary disk file is used when all available memory is used by the WATCOM Linker. 
Normally, the temporary file is created in the default directory.  However, by defining the "tmp" environment variable to be a directory, you can tell the WATCOM Linker where to create the temporary file.  This can be particularly useful if you have a RAM disk.  Consider the following definition of the "tmp" environment variable. 
    
   set tmp=\tmp 
The WATCOM Linker will create the temporary file in the directory "\tmp".


### DOS:  Using Overlays

Overlays are used primarily for large programs where memory requirements do not permit all portions of the program to reside in memory at the same time.  An overlayed program consists of a root and a number of overlay areas. 
The root always resides in memory.  The root usually contains routines that are frequently used.  For example, a floating-point library might be placed in the root.  Also, any modules extracted from a library file during the linking process are placed in the root unless the "DISTRIBUTE" option is specified.  This option tells the WATCOM Linker to distribute modules extracted from libraries throughout the overlay structure.  See the section entitled DOS:  The DISTRIBUTE Option for information on how these object modules are distributed.  Libraries can also be placed in the overlay structure by using the "FIXEDLIB" directive.  See the section entitled DOS:  The FIXEDLIB Directive for information on how to use this directive. 
An overlay area is a piece of memory shared by various parts of a program.  Each overlay area has a structure associated with it.  This structure defines where in the overlay area sections of a program are loaded.  Sections of a program that are loaded into an overlay area are called overlays. 
The WATCOM Linker supports two overlay managers:  the standard overlay manager and the dynamic overlay manager.  The standard overlay manager requires the user to create an overlay structure that defines the "call" relationship between the object modules that comprise an application.  It is the responsibility of the user to define an optimal overlay structure so as to minimize the number of calls that cause overlays to be loaded.  The "SMALL" and "STANDARD" options select the standard overlay manager.  The "SMALL" option is required if you are linking an application compiled for a small code memory model.  The "STANDARD" option is required if you are linking an application compiled for a big code memory model.  By default, the WATCOM Linker assumes your application has been compiled using a memory model with a big code model.  Option "STANDARD" is the default. 
The "DYNAMIC" option, described in the section entitled DOS:  The DYNAMIC Option, selects the dynamic overlay manager.  The dynamic overlay manager is more sophisticated than the standard overlay manager.  The user need not be concerned about the "call" relationship between the object modules that comprise an application.  Basically, each module is placed in its own overlay.  The dynamic overlay manager swaps each module (overlay) into a single overlay area.  This overlay area is used as a pool of memory from which memory for overlays is allocated.  The larger the memory pool, the greater the number of modules that can simultaneously reside in memory.  The size of the overlay area can be controlled by the "AREA" option.  See the section entitled DOS:  The AREA Option for information on using this option. 
Note that the dynamic overlay manager can only be used with applications that have been compiled using the "of" option and a big code memory model.


#### DOS:  Defining Overlay Structures

Consider the following directive file. 
    
   # 
   # Define files that belong in the root. 
   # 
   file file0, file1 
   # 
   # Define an overlay area. 
   # 
   begin 
    section file file2 
    section file file3, file4 
    section file file5 
   end 

 1.The root consists of file0 and file1. 

 2.Three overlays are defined.  The first overlay (overlay #1) contains file2, the second overlay (overlay #2) contains file3 and file4, and the third overlay (overlay #3) contains file5. 
The following diagram depicts the overlay structure. 
    
   +-----------------------------------+<- start of root 
   |                  | 
   |        file0        | 
   |        file1        | 
   |                  | 
   +-----------+-----------+-----------+<- start of overlay 
   | #1     | #2     | #3     |  area 
   |      |      |      | 
   |  file2  |  file3  |  file5  | 
   |      |  file4  |      | 
   |      |      |      | 
   +-----------+-----------+-----------+ 
Notes: 

 1.The 3 overlays are all loaded at the same memory location.  Such overlays are called  parallel. 
In the previous example, only one overlay area was defined.  It is possible to define more than one overlay area as demonstrated by the following example. 
    
   # 
   # Define files that belong in the root. 
   # 
   file file0, file1 
   # 
   # Define an overlay area. 
   # 
   begin 
    section file file2 
    section file file3, file4 
    section file file5 
   end 
   # 
   # Define an overlay area. 
   # 
   begin 
    section file file6 
    section file file7 
    section file file8 
   end 
Two overlay areas are defined.  The first is identical to the overlay area defined in the previous example.  The second overlay area contains three overlays; the first overlay (overlay #4) contains file6, the second overlay (overlay #5) contains file7, and the third overlay (overlay #6) contains file8. 
The following diagram depicts the overlay structure. 
    
   +-----------------------------------+<- start of root 
   |                  | 
   |        file0        | 
   |        file1        | 
   |                  | 
   +-----------+-----------+-----------+<- start of overlay 
   | #1     | #2     | #3     |  area 
   |      |      |      | 
   |  file2  |  file3  |  file5  | 
   |      |  file4  |      | 
   |      |      |      | 
   +-----------+-----------+-----------+<- start of overlay 
   | #4     | #5     | #6     |  area 
   |      |      |      | 
   |  file6  |  file7  |  file8  | 
   |      |      |      | 
   +-----------+-----------+-----------+ 
In the above example, the "AUTOSECTION" directive could have been used to define the overlays for the second overlay area.  The following example illustrates the use of the "AUTOSECTION" directive. 
    
   # 
   # Define files that belong in the root. 
   # 
   file file0, file1 
   # 
   # Define an overlay area. 
   # 
   begin 
    section file file2 
    section file file3, file4 
    section file file5 
   end 
   # 
   # Define an overlay area. 
   # 
   begin 
    autosection 
    file file6 
    file file7 
    file file8 
   end 
In all of the above examples the overlays are placed in the executable file.  It is possible to place overlays in separate files by specifying the "INTO" option in the "SECTION" directive that starts the definition of an overlay.  By specifying the "INTO" option in the "AUTOSECTION" directive, all overlays created as a result of the "AUTOSECTION" directive are placed in one overlay file. 
Consider the following example.  It is similar to the previous example except for the following.  Overlay #1 is placed in the file "ovl1.ovl", overlay #2 is placed in the file "ovl2.ovl", overlay #3 is placed in the file "ovl3.ovl" and overlays #4, #5 and #6 are placed in file "ovl4.ovl". 
    
   # 
   # Define files that belong in the root. 
   # 
   file file0, file1 
   # 
   # Define an overlay area. 
   # 
   begin 
    section into ovl1 file file2 
    section into ovl2 file file3, file4 
    section into ovl3 file file5 
   end 
   # 
   # Define an overlay area. 
   # 
   begin 
    autosection into ovl4 
    file file6 
    file file7 
    file file8 
   end


##### DOS:  The Dynamic Overlay Manager

Let us again consider the above example but this time we will use the dynamic overlay manager.  The easiest way to take the above overlay structure and use it with the dynamic overlay manager is to simply specify the "DYNAMIC" option. 
    
   option DYNAMIC 
Even though we have defined an overlay structure with more than one overlay area, the WATCOM Linker will allocate one overlay area and overlays from both overlay areas will be loaded into a single overlay area.  The size of the overlay area created by the WATCOM Linker will be twice the size of the largest overlay area (unless the "AREA" option is used). 
To take full advantage of the dynamic overlay manager, the following sequence of directives should be used. 
    
   # 
   # Define files that belong in the root. 
   # 
   file file0, file1 
   # 
   # Define an overlay area. 
   # 
   begin 
    autosection into ovl1 
    file file2 
    autosection into ovl2 
    file file3 
    file file4 
    autosection into ovl3 
    file file5 
    autosection into ovl4 
    file file6 
    file file7 
    file file8 
   end 
In the above example, each module will be in its own overlay.  This will result in a module being loaded into memory only when it is required.  If separate overlay files are not required, a single "AUTOSECTION" directive could be used as demonstrated by the following example. 
    
   # 
   # Define files that belong in the root. 
   # 
   file file0, file1 
   # 
   # Define an overlay area. 
   # 
   begin 
    autosection 
    file file2 
    file file3 
    file file4 
    file file5 
    file file6 
    file file7 
    file file8 
   end


#### DOS:  Nested Overlay Structures

Nested overlay structures occur when the "BEGIN"-"END" directives are nested and are only useful if the standard overlay manager is being used.  If you have selected the dynamic overlay manager, the nesting levels will be ignored and each overlay will be loaded into a single overlay area. 
Consider the following directive file. 
    
   # 
   # Define files that belong in the root. 
   # 
   file file0, file1 
   # 
   # Define a nested overlay structure. 
   # 
   begin 
    section file file2 
    section file file3 
    begin 
     section file file4, file5 
     section file file6 
    end 
   end 
Notes: 

 1.The root contains file0 and file1. 

 2.Four overlays are defined.  The first overlay (overlay #1) contains file2, the second overlay (overlay #2) contains file3, the third overlay (overlay #3) contains file4 and file5, and the fourth overlay (overlay #4) contains file6. 
The following diagram depicts the overlay structure. 
    
   +-----------------------------------+<- start of root 
   |                  | 
   |        file0        | 
   |        file1        | 
   |                  | 
   +-----------+-----------------------+<- start of overlay 
   | #1     | #2           |  area 
   |      |            | 
   |  file2  |     file3     | 
   |      |            | 
   |      |            | 
   |      +-----------+-----------+<- start of overlay 
   |      | #3     | #4     |  area 
   |      |      |      | 
   |      |  file4  |  file6  | 
   |      |  file5  |      | 
   |      |      |      | 
   +-----------+-----------+-----------+ 
Notes: 

 1.Overlay #1 and overlay #2 are parallel overlays.  Overlay #3 and overlay #4 are also parallel overlays. 

 2.Overlay #3 and overlay #4 are loaded in memory following overlay #2.  In this case, overlay #2 is called an  ancestor of overlay #3 and overlay #4.  Conversely, overlay #3 and overlay #4 are  descendants of overlay #2. 

 3.The root is an ancestor of all overlays. 
Nested overlays are particularly useful when the routines that make up one overlay are used only by a few other overlays.  In the above example, the routines in overlay #2 would only be used by routines in overlay #3 and overlay #4 but not by overlay #1.


#### DOS:  Rules About Overlays

The WATCOM Linker handles all the details of loading overlays.  No changes to a program have to be made if, for example, it becomes so large that you have to change to an overlay structure.  Certain rules have to be followed to ensure the proper execution of your program.  These rules pertain more to the organization of the components of your program and less to the way it was coded. 

 1.Care should be taken when passing addresses of functions as arguments.  Consider the following example. 
    
   +-----------------------+<- start of root 
   |            | 
   |     main      | 
   |            | 
   +-----------+-----------+<- start of overlay 
   |  modulea  |  moduleb  |  area 
   |      |      | 
   |   f   |   h   | 
   |   g   |      | 
   |      |      | 
   +-----------+-----------+ 
Function f passes the address of static function g to function h.  Function h then calls function g indirectly.  Function f and function g are defined in modulea and function h is defined in moduleb.  Furthermore, suppose that modulea and moduleb are parallel overlays.  The linker will not generate an overlay vector for function g since it is static so when function h calls function g indirectly, unpredictable results may occur.  Note that if g is a global function, an overlay vector will be generated and the program will execute correctly. 

 2.You should organize the overlay structure to minimize the number of times overlays have to be loaded into memory.  Consider a loop calling two routines, each routine in a different overlay.  If the overlay structure is such that the overlays are parallel, that is they occupy the same memory, each iteration of the loop will cause 2 overlays to be loaded into memory.  This will significantly increase execution time if the loop is iterated many times. 

 3.If a number of overlays have a number of common routines that they all reference, the common routines will most likely be placed in an ancestor overlay of the overlays that reference them.  For this reason, whenever an overlay is loaded, all its ancestors are also loaded. 

 4.In an overlayed program, the overlay loader is included in the executable file.  If we are dealing with relatively small programs, the size of the overlay loader may be larger than the amount of memory saved by overlaying the program.  In a larger application, the size of the overlayed version would be smaller than the size of the non-overlayed version.  Note that overlaying a program results in a larger executable file but the memory requirements are less. 

 5.The symbols "__OVLTAB__", "__OVLSTARTVEC__", "__OVLENDVEC__", "__LOVLLDR__", "__NOVLLDR__", "__SOVLLDR__", "__LOVLINIT__", "__NOVLINIT__" and "__SOVLINIT__" are defined when you use overlays.  Your program should not define these symbols. 

 6.When using the dynamic overlay manager, you should not take the address of static functions.  Static functions are not given overlay vectors, so if the module in which the address of a static function is taken, is moved by the dynamic overlay manager, that address will no longer point to the static function.


#### DOS:  Increasing the Dynamic Overlay Area

Unless the "AREA" option has been specified, the default size of the dynamic overlay area is twice the size of the largest overlay (or module if each module is its own overlay).  It is possible to add additional overlay areas at run-time so that the dynamic overlay manager can use the additional memory.  A routine has been provided, called _ovl_addarea.  This function is defined as follows. 
    
   void far _ovl_addarea(unsigned segment,unsigned size); 
The first argument is the segment address of the block memory you wish to add.  The second argument is the size, in paragraphs, of the memory block. 
In assembly language, the function is called _ovl_addarea_ with the first argument being passed in register AX and the second argument in register DX.


#### DOS:  How Overlay Files are Opened

The overlay manager normally opens overlay files, including executable files containing overlays, in compatibility mode.  Compatibility mode is a sharing mode.  A file opened in compatibility mode means that it can be opened any number of times provided that it is not currently opened under one of the other sharing modes.  In other words, the file must always be opened in compatibility mode. 
The overlay manager keeps most recently used overlay files open for efficiency.  This means that any application, including the currently executing application, that may want to open an overlay file, must open it in compatibility mode.  For example, the executing application may have data at the end of the executable file that it wishes to access. 
If an application wishes to open the file in a sharing mode other than compatibility mode, the function _ovl_openflags has been defined which allows the caller to specify the sharing mode with which the overlay files will be opened by the overlay manager.  This function is defined as follows. 
    
   unsigned far _ovl_openflags(unsigned sharing_mode); 
Legal values for the sharing mode are as follows. 
   Sharing Mode  Value 
   -----------------  ------- 
   compatibility 
   mode      0x00 
   deny read/write 
   mode      0x01 
   deny write 
   mode      0x02 
   deny read 
   mode      0x03 
   deny none 
   mode      0x04 
The return value is the previous sharing mode used by the overlay manager to open overlay files. 
Note that DOS opens executable files in compatibility mode when loading them for execution.  This is important for executable files on networks that may be accessed simultaneously by many users. 
In assembly language, the function is called _ovl_openflags_ with its argument being passed in register AX.


### DOS:  Converting Microsoft Response Files to Directive Files

A utility called MS2WLINK can be used to convert Microsoft linker response files to WATCOM Linker directive files.  Input to MS2WLINK is processed in the same way as the Microsoft linker processes its input, the difference being MS2WLINK lists the corresponding WATCOM Linker directive file to the standard output device instead of a creating an executable file.  The resulting output can be redirected to a disk file which can then be used as input to the WATCOM Linker to produce an executable file. 
Suppose you have a Microsoft linker response file called "test.rsp".  You can convert this file to a WATCOM Linker directive file by issuing the following command. 
Example: 
   ms2wlink @test.rsp >test.lnk 
You can now use the WATCOM Linker to link your program by issuing the following command. 
Example: 
   wlink @test 
An alternative way to link your application with the WATCOM Linker from a Microsoft response file is to issue the following command. 
Example: 
   ms2wlink @test.rsp | wlink 
Since the WATCOM Linker gets its input from the standard input device, you do not have to create a WATCOM Linker directive file to link your application. 
Note that MS2WLINK can also process module-definition files used for creating OS/2 applications.


## ELF:  The ELF Executable File Format

This chapter deals with those aspects of the WATCOM Linker required to generate ELF executable files.  The ELF executable file format will only run under the operating systems that support the ELF executable file format.


### ELF:  The WATCOM Linker Command Line

Input to the WATCOM Linker is specified on the command line.  The following notation is used to describe the syntax of WATCOM Linker commands. 

ABC All items in upper case are required. 

[abc] The item abc is optional. 

{abc} The item abc may be repeated zero or more times. 

{abc}+ The item abc may be repeated one or more times. 

a|b|c One of a, b or c may be specified. 

a ::= b The item a is defined in terms of b. 
The WATCOM Linker command line format is as follows. 
    
   WLINK {directive} 
where directive is any of the following: 

DEBUG [[WATCOM] db_list | CODEVIEW | DWARF] 
   db_list ::= db_option{,db_option} 
   db_option ::= LINES | TYPES | LOCALS | ALL 

| DISABLE msg_num{,msg_num} 

| EXPORT entry_name {,entry_name} 

| FILE obj_spec{,obj_spec} 
   obj_spec ::= obj_file[(obj_module)] | library_file[(obj_module)] 

| FORMAT ELF [DLL] 

| IMPORT external_name {,external_name} 

| LIBFILE obj_file{,obj_file} 

| LIBPATH path_name{;path_name} 

| LIBRARY library_file{,library_file} 

| MODTRACE obj_module{,obj_module} 

| MODULE module_name {,module_name} 

| NAME exe_file 

| OPTION option{,option} 
   option ::= ALIGNMENT=n | ARTIFICIAL | [NO]CACHE 
           | [NO]CASEEXACT | DOSSEG | ELIMINATE 
           | MANGLEDNAMES | MAP[=map_file] 
           | MAXERRORS=n | NAMELEN=n | NODEFAULTLIBS 
           | OSNAME='string' | PACKCODE=n | QUIET 
           | REDEFSOK | STACK=n | STATIC 
           | SYMFILE[=symbol_file] | UNDEFSOK | VERBOSE 

| PATH path_name{;path_name} 

| SORT [GLOBAL] [ALPHABETICAL] 

| SYMTRACE symbol_name{,symbol_name} 

| SYSTEM BEGIN system_name {directive} END 

| SYSTEM system_name 

| # comment 

| @ directive_file 

obj_file is a file specification for the name of an object file.  If no file extension is specified, a file extension of "obj" is assumed if you are running a DOS, OS/2 or Windows NT-hosted version of the WATCOM Linker.  Also, if you are running a DOS, OS/2 or Windows NT-hosted version of the WATCOM Linker, the object file specification can contain wild cards (*, ?).  A file extension of "o" is assumed if you are running a QNX-hosted version of the WATCOM Linker. 

library_file is a file specification for the name of a library file.  If library_file appears in a "LIBRARY" directive and no file extension is specified, a file extension of "lib" is assumed.  If library_file appears in a "FILE" directive and no file extension is specified, a file extension of "obj" is assumed if you are running a DOS, OS/2 or Windows NT-hosted version of the WATCOM Linker.  A file extension of "o" is assumed if you are running a QNX-hosted version of the WATCOM Linker. 
When a library file is specified in a "FILE" directive and obj_module is specified, the object module identified by obj_module is extracted from the library file and included in the executable file.  If obj_module is not specified (only the library file is specified), all object modules in the library are included in the executable file. 

obj_module is the name of an object module contained in a library file or object file. 
Object files may contain multiple object modules.  A simple way of creating such an object file is to concatenate a number of object files into a single object file.  Each of the original object files is now an object module in the resulting object file.  Also, some language processors may generate object files that contain multiple object modules.  Specifying obj_module allows you to select a particular object module from an object file. 

exe_file is a file specification for the name of the executable file.  If no file extension is specified, a file extension of "exe" is assumed.  If a dynamic link library file is being generated, a file extension of "dll" is assumed. 

path_name is a path name. 

msg_num is a message number. 

directive_file is a file specification for the name of a linker directive file.  If no file extension is specified, a file extension of "lnk" is assumed. 

map_file is a file specification for the name of the map file.  If no file extension is specified, a file extension of "map" is assumed. 

symbol_file is a file specification for the name of the symbol file.  If no file extension is specified, a file extension of "sym" is assumed. 

symbol_name is a symbol name. 

system_name is the name of a system. 

comment is any sequence of characters. 

n represents a value.  The complete form of n is the following. 
    
   [0x]d{d}[k|m] 
d represents a decimal digit.  If 0x is specified, the string of digits represents a hexadecimal number.  If k is specified, the value is multiplied by 1024.  If m is specified, the value is multiplied by 1024*1024. 
You can view all the directives specific to ELF executable files by simply typing the following: 
    
   wlink ? elf 
Notes: 

 1.If the file "wlink.hlp" is located in one of the paths specified in the "PATH" environment variable, the contents of that file will be displayed when the following command is issued. 
    
   wlink ? 

 2.If all of the directive information does not fit on the command line, type the following. 
    
   wlink 
The prompt "WLINK>" will appear on the next line.  You can enter as many lines of directive information as required.  Press "Ctrl/Z" followed by the "Enter" key to terminate the input of directive information if you are running a DOS, OS/2 or Windows NT-hosted version of the WATCOM Linker.  Press "Ctrl/D" to terminate the input of directive information if you are running a QNX-hosted version of the WATCOM Linker.


### ELF:  WATCOM Linker Directives

Directives tell the WATCOM Linker how to create your program.  For example, using directives you can tell the WATCOM Linker which object files are to be included in the program, which library files to search to resolve undefined references, and the name of the executable file. 
The file WLINK.LNK is a special linker directive file that is automatically processed by the WATCOM Linker before processing any other directives.  On a DOS, OS/2 or Windows NT-hosted system, this file should be located in one of the paths specified in the PATH environment variable.  On a QNX-hosted system, this file should be located in the /etc directory.  A default version of this file is located in the \WATCOM\BIN directory on DOS-hosted systems, the \WATCOM\BINP directory on OS/2-hosted systems, the /etc directory on QNX-hosted systems, and the \WATCOM\BINNT directory on Windows NT-hosted systems.  Note that the file WLINK.LNK includes the file WLSYSTEM.LNK which is located in the \WATCOM\BINB directory on DOS, OS/2 and Windows NT-hosted systems and the /etc directory on QNX-hosted systems. 
The files WLINK.LNK and WLSYSTEM.LNK reference the WATCOM environment variable which must be set to the directory in which you installed your software. 
It is also possible to use environment variables when specifying a directive.  For example, if the LIBDIR environment variable is defined as follows, 
    
   set libdir=\test 
then the linker directive 
    
   library %libdir%\mylib 
is equivalent to the following linker directive. 
    
   library \test\mylib 
Note that a space must precede a reference to an environment variable. 
The following sections describe those WATCOM Linker directives that are used to generate ELF executable files.


#### ELF:  The EXPORT Directive

The "EXPORT" directive is used to tell the WATCOM Linker which symbols are available for import by other executables.  The format of the "EXPORT" directive (short form "EXP") is as follows. 
    
     EXPORT entry_name{,entry_name} 

entry_name is the name of the exported symbol. 
 Note:  By default, the WATCOM C compiler appends an underscore ('_') to all function names.  This should be considered when specifying entry_name in an "EXPORT" directive.


#### ELF:  The FORMAT Directive

The "FORMAT" directive is used to specify the format of the executable file that the WATCOM Linker is to generate.  The format of the "FORMAT" directive (short form "FORM") is as follows. 
    
     FORMAT form 
     form ::= DOS [COM] 
           | WINDOWS [win_dll] [MEMORY] [FONT] 
           | WINDOWS NT [TNT] [dll_attrs] 
           | OS2 [os2_type] [dll_attrs | os2_attrs] 
           | PHARLAP [EXTENDED | REX] 
           | NOVELL [NLM | LAN | DSK | NAM] 'description' 
           | QNX [FLAT] 
           | ELF [DLL] 
     dll_attrs ::= DLL [INITGLOBAL | INITINSTANCE] 
              [TERMINSTANCE | TERMGLOBAL] 
     win_attrs ::= [win_dll] [MEMORY] [FONT] 
     win_dll ::= DLL [INITGLOBAL | INITINSTANCE] 
     os2_type ::= FLAT | LE | LX 
     os2_attrs ::= PM | PMCOMPATIBLE | FULLSCREEN 
               | PHYSDEVICE | VIRTDEVICE 

DOS (short form "D") tells the WATCOM Linker to generate a DOS "EXE" file.  For more information on DOS executable file formats, see the chapter entitled DOS:  The DOS Executable File Format. 

WINDOWS tells the WATCOM Linker to generate a Windows executable file.  For more information on Windows executable file formats, see the chapter entitled Windows:  The Windows Executable and DLL File Formats. 

WINDOWS NT tells the WATCOM Linker to generate a Windows NT executable file ("PE" format).  For more information on Windows NT executable file formats, see the chapter entitled NT:  The Windows NT Executable and DLL File Formats. 

OS2 tells the WATCOM Linker to generate an OS/2 executable file format.  For more information on OS/2 executable file formats, see the chapter entitled OS/2:  The OS/2 Executable and DLL File Formats. 

PHARLAP (short form "PHAR") tells the WATCOM Linker to generate an executable file that will run under Phar Lap's 386|DOS-Extender.  For more information on Phar Lap executable file formats, see the chapter entitled Phar Lap:  The Phar Lap Executable File Format. 

NOVELL (short form "NOV") tells the WATCOM Linker to generate a NetWare 386 executable file, more commonly called a NetWare Loadable Module (NLM).  For more information on NetWare 386 executable file formats, see the chapter entitled NetWare:  The NetWare 386 Executable File Format. 

QNX tells the WATCOM Linker to generate a QNX executable file.  For more information on QNX executable file formats, see the chapter entitled QNX:  The QNX Executable File Format. 

ELF tells the WATCOM Linker to generate an ELF format executable file.  ELF format DLLs can also be created. 
If no "FORMAT" directive is specified and you are running a DOS, OS/2 or Windows NT-hosted version of the WATCOM Linker, the executable file format will be selected in the following way. 

 1.If a reference to a dynamic link library is encountered, an OS/2 executable file will be generated. 

 2.If a 386 object module is encountered, an executable file that runs under Phar Lap's 386|DOS-Extender will be generated. 

 3.Otherwise, a DOS executable file will be generated. 
If no "FORMAT" directive is specified and you are running a QNX-hosted version of the WATCOM Linker, the executable file format will be selected in the following way. 

 1.If a reference to a dynamic link library is encountered, an OS/2 format executable file will be generated. 

 2.If a 386 object module is encountered, an executable file that runs under Phar Lap's 386|DOS-Extender will be generated. 

 3.Otherwise, a QNX executable file will be generated.


#### ELF:  The IMPORT Directive

The "IMPORT" directive is used to tell the WATCOM Linker what symbols are defined externally in other executables.  The format of the "IMPORT" directive (short form "IMP") is as follows. 
    
     IMPORT external_name{,external_name} 

external_name is the name of the external symbol. 
 Note:  By default, the WATCOM C compiler appends an underscore ('_') to all function names.  This should be considered when specifying external_name in an "IMPORT" directive.


#### ELF:  The MODULE Directive

The "MODULE" directive is used to specify the DLLs to be loaded before this executable is loaded.  The format of the "MODULE" directive (short form "MODU") is as follows. 
    
     MODULE module_name{,module_name} 

module_name is the file name of a DLL.


#### ELF:  The OPTION Directive

The "OPTION" directive is used to specify options to the WATCOM Linker.  The format of the "OPTION" directive (short form "OP") is as follows. 
    
     OPTION option{,option} 
     option ::= ALIGNMENT=n | ARTIFICIAL | [NO]CACHE 
             | [NO]CASEEXACT | DOSSEG | ELIMINATE 
             | MANGLEDNAMES | MAP[=map_file] 
             | MAXERRORS=n | NAMELEN=n | NODEFAULTLIBS 
             | OSNAME='string' | PACKCODE=n | QUIET 
             | REDEFSOK | STACK=n | STATIC 
             | SYMFILE[=symbol_file] | UNDEFSOK | VERBOSE 

map_file is a file specification for the name of the map file.  If no file extension is specified, a file extension of "map" is assumed. 

symbol_file is a file specification for the name of the symbol file.  If no file extension is specified, a file extension of "sym" is assumed. 

n represents a value.  The complete form of n is the following. 
    
   [0x]d{d}[k|m] 
d represents a decimal digit.  If 0x is specified, the string of digits represents a hexadecimal number.  If k is specified, the value is multiplied by 1024.  If m is specified, the value is multiplied by 1024*1024. 
The following sections describe the WATCOM Linker options specific to this executable format.  The options common to all executable formats are described in the chapter entitled General Directives and Options.


##### ELF:  The ALIGNMENT Option

The "ALIGNMENT" option specifies the alignment for segments in the executable file.  The format of the "ALIGNMENT" option (short form "A") is as follows. 
    
     OPTION ALIGNMENT=n 

n represents a value.  The complete form of n is the following. 
    
   [0x]d{d}[k|m] 
d represents a decimal digit.  If 0x is specified, the string of digits represents a hexadecimal number.  If k is specified, the value is multiplied by 1024.  If m is specified, the value is multiplied by 1024*1024. 
n specifies the alignment for segments in the executable file and must be a power of 2.


### ELF:  Memory Layout

The following describes the segment ordering of an application linked by the WATCOM Linker.  Note that this assumes that the "DOSSEG" linker option has been specified. 

 1.all segments not belonging to group "DGROUP" with class "CODE" 

 2.all other segments not belonging to group "DGROUP" 

 3.all segments belonging to group "DGROUP" with class "BEGDATA" 

 4.all segments belonging to group "DGROUP" not with class "BEGDATA", "BSS" or "STACK" 

 5.all segments belonging to group "DGROUP" with class "BSS" 

 6.all segments belonging to group "DGROUP" with class "STACK" 
A special segment belonging to class "BEGDATA" is defined when linking with WATCOM run-time libraries.  This segment is initialized with the hexadecimal byte pattern "01" and is the first segment in group "DGROUP" so that storing data at location 0 can be detected. 
Segments belonging to class "BSS" contain uninitialized data.  Note that this only includes uninitialized data in segments belonging to group "DGROUP".  Segments belonging to class "STACK" are used to define the size of the stack used for your application.  Segments belonging to the classes "BSS" and "STACK" are last in the segment ordering so that uninitialized data need not take space in the executable file.


### ELF:  The WATCOM Linker Memory Requirements

The WATCOM Linker uses all available memory when linking an application.  For DOS-hosted versions of the WATCOM Linker, this includes expanded memory (EMS) and extended memory.  It is possible for the size of the image being linked to exceed the amount of memory available in your machine, particularly if the image file is to contain debugging information. For this reason, a temporary disk file is used when all available memory is used by the WATCOM Linker. 
Normally, the temporary file is created in the default directory.  However, by defining the "tmp" environment variable to be a directory, you can tell the WATCOM Linker where to create the temporary file.  This can be particularly useful if you have a RAM disk.  Consider the following definition of the "tmp" environment variable. 
    
   set tmp=\tmp 
The WATCOM Linker will create the temporary file in the directory "\tmp".


## NetWare:  The NetWare 386 Executable File Format

This chapter deals with those aspects of the WATCOM Linker required to generate NetWare 386 executable files.  The Novell NetWare 386 executable file format will only run under the NetWare 386 operating system.


### NetWare:  The WATCOM Linker Command Line

Input to the WATCOM Linker is specified on the command line.  The following notation is used to describe the syntax of WATCOM Linker commands. 

ABC All items in upper case are required. 

[abc] The item abc is optional. 

{abc} The item abc may be repeated zero or more times. 

{abc}+ The item abc may be repeated one or more times. 

a|b|c One of a, b or c may be specified. 

a ::= b The item a is defined in terms of b. 
The WATCOM Linker command line format is as follows. 
    
   WLINK {directive} 
where directive is any of the following: 

DEBUG [[WATCOM] db_list | CODEVIEW | DWARF | NOVELL [ONLYEXPORTS]] 
   db_list ::= db_option{,db_option} 
   db_option ::= LINES | TYPES | LOCALS | ALL | ONLYEXPORTS 

| DISABLE msg_num{,msg_num} 

| EXPORT entry_name {,entry_name} 

| FILE obj_spec{,obj_spec} 
   obj_spec ::= obj_file[(obj_module)] | library_file[(obj_module)] 

| FORMAT NOVELL [NLM | LAN | DSK | NAM] 'description' 

| IMPORT external_name {,external_name} 

| LIBFILE obj_file{,obj_file} 

| LIBPATH path_name{;path_name} 

| LIBRARY library_file{,library_file} 

| MODTRACE obj_module{,obj_module} 

| MODULE module_name {,module_name} 

| NAME exe_file 

| OPTION option{,option} 
   option ::= ARTIFICIAL | [NO]CACHE | [NO]CASEEXACT 
           | CHECK=symbol_name | COPYRIGHT 'string' 
           | CUSTOM=file_name | DOSSEG | ELIMINATE 
           | EXIT=symbol_name | MANGLEDNAMES 
           | MAP[=map_file] | MAXERRORS=n | MULTILOAD 
           | NAMELEN=n | NODEFAULTLIBS | OSNAME='string' 
           | PACKCODE=n | PSEUDOPREEMPTION | QUIET 
           | REDEFSOK | REENTRANT | SCREENNAME 'name' 
           | STACK=n | START=symbol_name | STATIC 
           | SYMFILE[=symbol_file] | SYNCHRONIZE 
           | THREADNAME 'thread_name' | UNDEFSOK 
           | VERBOSE | VERSION=major.minor[.revision] 

| PATH path_name{;path_name} 

| SORT [GLOBAL] [ALPHABETICAL] 

| SYMTRACE symbol_name{,symbol_name} 

| SYSTEM BEGIN system_name {directive} END 

| SYSTEM system_name 

| # comment 

| @ directive_file 

obj_file is a file specification for the name of an object file.  If no file extension is specified, a file extension of "obj" is assumed if you are running a DOS, OS/2 or Windows NT-hosted version of the WATCOM Linker.  Also, if you are running a DOS, OS/2 or Windows NT-hosted version of the WATCOM Linker, the object file specification can contain wild cards (*, ?).  A file extension of "o" is assumed if you are running a QNX-hosted version of the WATCOM Linker. 

library_file is a file specification for the name of a library file.  If library_file appears in a "LIBRARY" directive and no file extension is specified, a file extension of "lib" is assumed.  If library_file appears in a "FILE" directive and no file extension is specified, a file extension of "obj" is assumed if you are running a DOS, OS/2 or Windows NT-hosted version of the WATCOM Linker.  A file extension of "o" is assumed if you are running a QNX-hosted version of the WATCOM Linker. 
When a library file is specified in a "FILE" directive and obj_module is specified, the object module identified by obj_module is extracted from the library file and included in the executable file.  If obj_module is not specified (only the library file is specified), all object modules in the library are included in the executable file. 

obj_module is the name of an object module contained in a library file or object file. 
Object files may contain multiple object modules.  A simple way of creating such an object file is to concatenate a number of object files into a single object file.  Each of the original object files is now an object module in the resulting object file.  Also, some language processors may generate object files that contain multiple object modules.  Specifying obj_module allows you to select a particular object module from an object file. 

exe_file is a file specification for the name of the executable file.  If no file extension is specified, a file extension of "nlm", "dsk", "lan" or "nam" is assumed depending on the executable file format selected. 

path_name is a path name. 

msg_num is a message number. 

directive_file is a file specification for the name of a linker directive file.  If no file extension is specified, a file extension of "lnk" is assumed. 

map_file is a file specification for the name of the map file.  If no file extension is specified, a file extension of "map" is assumed. 

symbol_file is a file specification for the name of the symbol file.  If no file extension is specified, a file extension of "sym" is assumed. 

symbol_name is a symbol name. 

system_name is the name of a system. 

description is any sequence of characters. 

name is any sequence of characters. 

comment is any sequence of characters. 

n represents a value.  The complete form of n is the following. 
    
   [0x]d { d } [ k | m ]
drepresentsadecimaldigit . If0xisspecified ,thestringofdigitsrepresentsahexadecimalnumber . Ifkisspecified ,thevalueismultipliedby1024 . Ifmisspecified ,thevalueismultipliedby1024 * 1024 .
YoucanviewallthedirectivesspecifictoNetWare386executablefilesbysimplytypingthefollowing :
    
   wlink?nov
Notes :

 1.If the file "wlink.hlp" is located in one of the paths specified in the "PATH" environment variable, the contents of that file will be displayed when the following command is issued. 
    
   wlink ? 

 2.If all of the directive information does not fit on the command line, type the following. 
    
   wlink 
The prompt "WLINK>" will appear on the next line.  You can enter as many lines of directive information as required.  Press "Ctrl/Z" followed by the "Enter" key to terminate the input of directive information if you are running a DOS, OS/2 or Windows NT-hosted version of the WATCOM Linker.  Press "Ctrl/D" to terminate the input of directive information if you are running a QNX-hosted version of the WATCOM Linker.


### NetWare:  NetWare Loadable Modules

NetWare Loadable Modules (NLMs) are executable files that run in file server memory under the NetWare 386 operating system.  NLMs can be loaded and unloaded from file server memory while the server is running.  When running they actually become part of the operating system thus acting as building blocks for a server environment tailored to your needs. 
There are four types of NLMs, each identified by the file extension of the executable file. 

oUtility and server applications (executable files with extension "nlm"). 
oLAN drivers (executable files with extension "lan"). 
oDisk drivers (executable files with extension "dsk"). 
oModules that define file system name spaces (executable files with extension "nam"). 
The WATCOM Linker can generate all four types of NLMs.


### NetWare:  WATCOM Linker Directives

Directives tell the WATCOM Linker how to create your program.  For example, using directives you can tell the WATCOM Linker which object files are to be included in the program, which library files to search to resolve undefined references, and the name of the executable file. 
The file WLINK.LNK is a special linker directive file that is automatically processed by the WATCOM Linker before processing any other directives.  On a DOS, OS/2 or Windows NT-hosted system, this file should be located in one of the paths specified in the PATH environment variable.  On a QNX-hosted system, this file should be located in the /etc directory.  A default version of this file is located in the \WATCOM\BIN directory on DOS-hosted systems, the \WATCOM\BINP directory on OS/2-hosted systems, the /etc directory on QNX-hosted systems, and the \WATCOM\BINNT directory on Windows NT-hosted systems.  Note that the file WLINK.LNK includes the file WLSYSTEM.LNK which is located in the \WATCOM\BINB directory on DOS, OS/2 and Windows NT-hosted systems and the /etc directory on QNX-hosted systems. 
The files WLINK.LNK and WLSYSTEM.LNK reference the WATCOM environment variable which must be set to the directory in which you installed your software. 
It is also possible to use environment variables when specifying a directive.  For example, if the LIBDIR environment variable is defined as follows, 
    
   set libdir=\test 
then the linker directive 
    
   library %libdir%\mylib 
is equivalent to the following linker directive. 
    
   library \test\mylib 
Note that a space must precede a reference to an environment variable. 
The following sections describe those WATCOM Linker directives that are used to generate NetWare 386 executable files.


#### NetWare:  The EXPORT Directive

The "EXPORT" directive is used to tell the WATCOM Linker which symbols are available for import by other NLMs.  The format of the "EXPORT" directive (short form "EXP") is as follows. 
    
     EXPORT entry_name{,entry_name} 

entry_name is the name of the exported symbol. 
 Note:  By default, the WATCOM C compiler appends an underscore ('_') to all function names.  This should be considered when specifying entry_name in an "EXPORT" directive.


#### NetWare:  The FORMAT Directive

The "FORMAT" directive is used to specify the format of the executable file that the WATCOM Linker is to generate.  The format of the "FORMAT" directive (short form "FORM") is as follows. 
    
     FORMAT form 
     form ::= DOS [COM] 
           | WINDOWS [win_dll] [MEMORY] [FONT] 
           | WINDOWS NT [TNT] [dll_attrs] 
           | OS2 [os2_type] [dll_attrs | os2_attrs] 
           | PHARLAP [EXTENDED | REX] 
           | NOVELL [NLM | LAN | DSK | NAM] 'description' 
           | QNX [FLAT] 
           | ELF [DLL] 
     dll_attrs ::= DLL [INITGLOBAL | INITINSTANCE] 
              [TERMINSTANCE | TERMGLOBAL] 
     win_attrs ::= [win_dll] [MEMORY] [FONT] 
     win_dll ::= DLL [INITGLOBAL | INITINSTANCE] 
     os2_type ::= FLAT | LE | LX 
     os2_attrs ::= PM | PMCOMPATIBLE | FULLSCREEN 
               | PHYSDEVICE | VIRTDEVICE 

DOS (short form "D") tells the WATCOM Linker to generate a DOS "EXE" file.  For more information on DOS executable file formats, see the chapter entitled DOS:  The DOS Executable File Format. 

WINDOWS tells the WATCOM Linker to generate a Windows executable file.  For more information on Windows executable file formats, see the chapter entitled Windows:  The Windows Executable and DLL File Formats. 

WINDOWS NT tells the WATCOM Linker to generate a Windows NT executable file ("PE" format).  For more information on Windows NT executable file formats, see the chapter entitled NT:  The Windows NT Executable and DLL File Formats. 

OS2 tells the WATCOM Linker to generate an OS/2 executable file format.  For more information on OS/2 executable file formats, see the chapter entitled OS/2:  The OS/2 Executable and DLL File Formats. 

PHARLAP (short form "PHAR") tells the WATCOM Linker to generate an executable file that will run under Phar Lap's 386|DOS-Extender.  For more information on Phar Lap executable file formats, see the chapter entitled Phar Lap:  The Phar Lap Executable File Format. 

NOVELL (short form "NOV") tells the WATCOM Linker to generate a NetWare 386 executable file, more commonly called a NetWare Loadable Module (NLM).  NLMs are further classified according to their function.  The executable file will have a file extension that depends on the class of the NLM being generated.  The following describes the classification of NLMs. 

LAN instructs the WATCOM Linker to generate a LAN driver.  A LAN driver is a device driver for Local Area Network hardware.  A file extension of "lan" is used for the name of the executable file. 

DSK instructs the WATCOM Linker to generate a disk driver.  A file extension of "dsk" is used for the name of the executable file. 

NAM instructs the WATCOM Linker to generate a file system name-space support module.  A file extension of "nam" is used for the name of the executable file. 

NLM instructs the WATCOM Linker to generate a utility or server application.  This is the default.  A file extension of "nlm" is used for the name of the executable file. 

description is a textual description of the program being linked. 

QNX tells the WATCOM Linker to generate a QNX executable file.  For more information on QNX executable file formats, see the chapter entitled QNX:  The QNX Executable File Format. 

ELF tells the WATCOM Linker to generate an ELF format executable file. 
If no "FORMAT" directive is specified and you are running a DOS, OS/2 or Windows NT-hosted version of the WATCOM Linker, the executable file format will be selected in the following way. 

 1.If a reference to a dynamic link library is encountered, an OS/2 executable file will be generated. 

 2.If a 386 object module is encountered, an executable file that runs under Phar Lap's 386|DOS-Extender will be generated. 

 3.Otherwise, a DOS executable file will be generated. 
If no "FORMAT" directive is specified and you are running a QNX-hosted version of the WATCOM Linker, the executable file format will be selected in the following way. 

 1.If a reference to a dynamic link library is encountered, an OS/2 format executable file will be generated. 

 2.If a 386 object module is encountered, an executable file that runs under Phar Lap's 386|DOS-Extender will be generated. 

 3.Otherwise, a QNX executable file will be generated.


#### NetWare:  The IMPORT Directive

The "IMPORT" directive is used to tell the WATCOM Linker what symbols are defined externally in other NLMs.  The format of the "IMPORT" directive (short form "IMP") is as follows. 
    
     IMPORT external_name{,external_name} 

external_name is the name of the external symbol. 
 Note:  By default, the WATCOM C compiler appends an underscore ('_') to all function names.  This should be considered when specifying external_name in an "IMPORT" directive. 
If an NLM contains external symbols, the NLMs that define the external symbols must be loaded before the NLM that references the external symbols is loaded.


#### NetWare:  The MODULE Directive

The "MODULE" directive is used to specify the NLMs to be loaded before this NLM is loaded.  The format of the "MODULE" directive (short form "MODU") is as follows. 
    
     MODULE module_name{,module_name} 

module_name is the file name of an NLM. 
 WARNING!  Versions 3.0 and 3.1 of the NetWare 386 operating system do not support the automatic loading of modules specified in the "MODULE" directive.  You must load them manually.


#### NetWare:  The OPTION Directive

The "OPTION" directive is used to specify options to the WATCOM Linker.  The format of the "OPTION" directive (short form "OP") is as follows. 
    
     OPTION option{,option} 
     option ::= ARTIFICIAL | [NO]CACHE | [NO]CASEEXACT 
             | CHECK=symbol_name | COPYRIGHT 'string' 
             | CUSTOM=file_name | DOSSEG | ELIMINATE 
             | EXIT=symbol_name | MANGLEDNAMES 
             | MAP[=map_file] | MAXERRORS=n | MULTILOAD 
             | NAMELEN=n | NODEFAULTLIBS | OSNAME='string' 
             | PACKCODE=n | PSEUDOPREEMPTION | QUIET 
             | REDEFSOK | REENTRANT | SCREENNAME 'name' 
             | STACK=n | START=symbol_name | STATIC 
             | SYMFILE[=symbol_file] | SYNCHRONIZE 
             | THREADNAME 'thread_name' | UNDEFSOK 
             | VERBOSE | VERSION=major.minor[.revision] 

map_file is a file specification for the name of the map file.  If no file extension is specified, a file extension of "map" is assumed. 

symbol_file is a file specification for the name of the symbol file.  If no file extension is specified, a file extension of "sym" is assumed. 

symbol_name is a symbol name. 

name is any sequence of characters. 

file_name is the name of the custom data file. 

thread_name is a symbol name. 

n represents a value.  The complete form of n is the following. 
    
   [0x]d{d}[k|m] 
d represents a decimal digit.  If 0x is specified, the string of digits represents a hexadecimal number.  If k is specified, the value is multiplied by 1024.  If m is specified, the value is multiplied by 1024*1024. 
The following sections describe the WATCOM Linker options specific to this executable format.  The options common to all executable formats are described in the chapter entitled General Directives and Options.


##### NetWare:  The CHECK Option

The "CHECK" option specifies the name of a procedure to execute before an NLM is unloaded.  This procedure can, for example, inform the operator that the NLM is in use and prevent it from being unloaded. 
The format of the "CHECK" option (short form "CH") is as follows. 
    
     OPTION CHECK=symbol_name 

symbol_name specifies the name of a procedure to execute before the NLM is unloaded. 
If the "CHECK" option is not specified, no check procedure will be called.


##### NetWare:  The COPYRIGHT Option

The "COPYRIGHT" option specifies copyright information that is placed in the executable file.  The format of the "COPYRIGHT" option (short form "COPYR") is as follows. 
    
     OPTION COPYRIGHT='string' 

string specifies the copyright information.


##### NetWare:  The CUSTOM Option

The format of the "CUSTOM" option (short form "CUST") is as follows. 
    
     OPTION CUSTOM=file_name 

file_name specifies the file name of the custom data file. 
The custom data file is placed into the executable file when the application is linked but is really not part of the program.  When the application is loaded into memory, the information extracted from a custom data file is not loaded into memory.  Instead, information is passed to the program (as arguments) which allows the access and processing of this information.


##### NetWare:  The EXIT Option

The format of the EXIT option is as follows. 
    
     OPTION EXIT=symbol_name 

symbol_name specifies the name of the procedure that is executed when an NLM is unloaded. 
The default name of the exit procedure is "_Stop". 
Note that the exit procedure cannot prevent the NLM from being unloaded.  Once the exit procedure has executed, the NLM will be unloaded.  The "CHECK" option can be used to specify a check procedure that can prevent an NLM from being unloaded.


##### NetWare:  The MULTILOAD Option

The "MULTILOAD" option specifies that the module can be loaded more than once by a "load" command.  The format of the "MULTILOAD" option (short form "MULTIL") is as follows. 
    
     OPTION MULTILOAD 
If the "MULTILOAD" option is not specified, it will not be possible to load the module more than once using the "load" command.


##### NetWare:  The PSEUDOPREEMPTION Option

The "PSEUDOPREEMPTION" option specifies that an additional set of system calls will yield control to other processes.  Multitasking in the NetWare 386 operating system is non-preemptive.  That is, a process must give up control in order for other processes to execute.  Using the "PSEUDOPREEMTION" option increases the probability that all processes are given an equal amount of CPU time. 
The format of the "PSEUDOPREEMPTION" option (short form "PS") is as follows. 
    
     OPTION PSEUDOPREEMPTION


##### NetWare:  The REENTRANT Option

The "REENTRANT" option specifies that the module is reentrant.  That is, if an NLM is LOADed twice, the actual code in the server's memory is reused.  The NLM's start procedure is called once for each LOAD.  The format of the "REENTRANT" option (short form "RE") is as follows. 
    
     OPTION REENTRANT


##### NetWare:  The SCREENNAME Option

The "SCREENNAME" option specifies the name of the first screen (the screen that is automatically created when an NLM is loaded).  The format of the "SCREENNAME" option (short form "SCR") is as follows. 
    
     OPTION SCREENNAME 'name' 

name specifies the screen name. 
If the "SCREENNAME" option is not specified, the description text specified in the "FORMAT" directive is used as the screen name.


##### NetWare:  The START Option

The format of the "START" option is as follows. 
    
     OPTION START=symbol_name 

symbol_name specifies the name of the procedure where execution begins. 
The default name of the start procedure is "_Prelude".


##### NetWare:  The SYNCHRONIZE Option

The "SYNCHRONIZE" option forces an NLM to complete loading before starting to load other NLMs.  Normally, the other NLMs are loading during the startup procedure.  The format of the "SYNCHRONIZE" option (short form "SY") is as follows. 
    
     OPTION SYNCHRONIZE


##### NetWare:  The THREADNAME Option

The "THREADNAME" option is used to specify the pattern to be used for generating thread names.  The format of the "THREADNAME" option (short form "THR") is as follows. 
    
     OPTION THREADNAME 'thread_name' 

thread_name specifies the pattern used for generating thread names and must be a string of 1 to 5 characters. 
The first thread name is generated by appending "0" to thread_name, the second by appending "1" to thread_name, etc.  If the "THREADNAME" option is not specified, the first 5 characters of the description specified in the "FORMAT" directive are used as the pattern for generating thread names.


##### NetWare:  The VERSION Option

The "VERSION" option can be used to identify the application so that it can be distinguished from other versions (releases) of the same application. 
The format of the "VERSION" option (short form "VER") is as follows. 
    
     OPTION VERSION=major.minor[.revision] 

major specifies the major version number. 

minor specifies the minor version number and must be less than 100. 

revision specified the revision.  The revision should be a number or a letter.  If it is a number, it must be less than 27.


### NetWare:  Memory Layout

The following describes the segment ordering of an application linked by the WATCOM Linker.  Note that this assumes that the "DOSSEG" linker option has been specified. 

 1.all segments not belonging to group "DGROUP" with class "CODE" 

 2.all other segments not belonging to group "DGROUP" 

 3.all segments belonging to group "DGROUP" with class "BEGDATA" 

 4.all segments belonging to group "DGROUP" not with class "BEGDATA", "BSS" or "STACK" 

 5.all segments belonging to group "DGROUP" with class "BSS" 

 6.all segments belonging to group "DGROUP" with class "STACK" 
A special segment belonging to class "BEGDATA" is defined when linking with WATCOM run-time libraries.  This segment is initialized with the hexadecimal byte pattern "01" and is the first segment in group "DGROUP" so that storing data at location 0 can be detected. 
Segments belonging to class "BSS" contain uninitialized data.  Note that this only includes uninitialized data in segments belonging to group "DGROUP".  Segments belonging to class "STACK" are used to define the size of the stack used for your application.  Segments belonging to the classes "BSS" and "STACK" are last in the segment ordering so that uninitialized data need not take space in the executable file.


### NetWare:  The WATCOM Linker Memory Requirements

The WATCOM Linker uses all available memory when linking an application.  For DOS-hosted versions of the WATCOM Linker, this includes expanded memory (EMS) and extended memory.  It is possible for the size of the image being linked to exceed the amount of memory available in your machine, particularly if the image file is to contain debugging information. For this reason, a temporary disk file is used when all available memory is used by the WATCOM Linker. 
Normally, the temporary file is created in the default directory.  However, by defining the "tmp" environment variable to be a directory, you can tell the WATCOM Linker where to create the temporary file.  This can be particularly useful if you have a RAM disk.  Consider the following definition of the "tmp" environment variable. 
    
   set tmp=\tmp 
The WATCOM Linker will create the temporary file in the directory "\tmp".


## OS/2:  The OS/2 Executable and DLL File Formats

This chapter deals with those aspects of the WATCOM Linker required to generate OS/2 executable files.  The OS/2 16-bit executable file format will run under the following operating systems. 

 1.OS/2 1.x 

 2.OS/2 2.x 

 3.Phar Lap's 286|DOS-Extender 
The OS/2 32-bit linear executable file format will run under the following operating systems. 

 1.OS/2 2.x (LX format only) 

 2.Tenberry Software's DOS/4G and DOS/4GW DOS Extenders (LE format only) 

 3.FlashTek's DOS Extender (LX format only)


### OS/2:  The WATCOM Linker Command Line

Input to the WATCOM Linker is specified on the command line.  The following notation is used to describe the syntax of WATCOM Linker commands. 

ABC All items in upper case are required. 

[abc] The item abc is optional. 

{abc} The item abc may be repeated zero or more times. 

{abc}+ The item abc may be repeated one or more times. 

a|b|c One of a, b or c may be specified. 

a ::= b The item a is defined in terms of b. 
The WATCOM Linker command line format is as follows. 
    
   WLINK {directive} 
where directive is any of the following: 

ALIAS alias_name=symbol_name{,alias_name=symbol_name} 

| DEBUG [[WATCOM] db_list | CODEVIEW | DWARF] 
   db_list ::= [db_option{,db_option}] 
   db_option ::= LINES | TYPES | LOCALS | STATIC | ALL 

| DISABLE msg_num{,msg_num} 

| EXPORT export{,export} 

| EXPORT =lbc_file 
   export ::= entry_name[.n][=internal_name] [RESIDENT] [n] 

| FILE obj_spec{,obj_spec} 
   obj_spec ::= obj_file[(obj_module)] | library_file[(obj_module)] 

| FORMAT OS2 [exe_type] [dll_form | exe_attrs] 
   exe_type ::= FLAT | LE | LX 
   dll_form ::= DLL [INITGLOBAL | INITINSTANCE] 
            [TERMGLOBAL | TERMINSTANCE] 
   exe_attrs ::= PM | PMCOMPATIBLE | FULLSCREEN 
            | PHYSDEVICE | VIRTDEVICE 

| IMPORT import{,import} 
   import ::= internal_name module_name[.entry_name | n] 

| LIBFILE obj_file{,obj_file} 

| LIBPATH path_name{;path_name} 

| LIBRARY library_file{,library_file} 

| MODTRACE obj_module{,obj_module} 

| NAME exe_file 

| NEWSEGMENT 

| PATH path_name{;path_name} 

| OPTION option{,option} 
   option ::= ALIGNMENT=n | ARTIFICIAL 
           | [NO]CACHE | [NO]CASEEXACT 
           | DESCRIPTION 'string' 
           | DOSSEG | ELIMINATE | HEAPSIZE=n 
           | INTERNALRELOCS 
           | MANGLEDNAMES | MANYAUTODATA 
           | MAP[=map_file] | MAXERRORS=n 
           | MODNAME=module_name | NAMELEN=n 
           | NEWFILES 
           | NOAUTODATA | NODEFAULTLIBS 
           | OFFSET 
           | OLDLIBRARY=dll_name | ONEAUTODATA 
           | OSNAME='string' | PACKCODE=n | PACKDATA=n 
           | PROTMODE 
           | QUIET | REDEFSOK 
           | STACK=n | STATIC | STUB=stub_name 
           | SYMFILE[=symbol_file] | UNDEFSOK 
           | VERBOSE | VERSION=major[.minor] 

| SEGMENT seg_desc{,seg_desc} 
   seg_desc ::= seg_id {seg_attrs}+ 
   seg_id ::= 'seg_name' | CLASS 'class_name' | TYPE [CODE | DATA] 
   seg_attrs ::= PRELOAD | LOADONCALL 
             | IOPL | NOIOPL 
             | EXECUTEONLY | EXECUTEREAD 
             | READONLY | READWRITE 
             | SHARED | NONSHARED 
             | CONFORMING | NONCONFORMING 

| SORT [GLOBAL] [ALPHABETICAL] 

| SYMTRACE symbol_name{,symbol_name} 

| SYSTEM BEGIN system_name {directive} END 

| SYSTEM system_name 

| # comment 

| @ directive_file 

class_name is a class name. 

comment is any sequence of characters. 

string is a sequence of characters. 

directive_file is a file specification for the name of a linker directive file.  If no file extension is specified, a file extension of "lnk" is assumed. 

dll_name is a file specification for the name of a dynamic link library.  If no file extension is specified, a file extension of "dll" is assumed. 

entry_name is a function name. 

exe_file is a file specification for the name of the executable file.  If no file extension is specified, a file extension of "exe" is assumed.  If a dynamic link library file is being generated, a file extension of "dll" is assumed. 

internal_name is a function name. 

library_file is a file specification for the name of a library file.  If library_file appears in a "LIBRARY" directive and no file extension is specified, a file extension of "lib" is assumed.  If library_file appears in a "FILE" directive and no file extension is specified, a file extension of "obj" is assumed if you are running a DOS, OS/2 or Windows NT-hosted version of the WATCOM Linker.  A file extension of "o" is assumed if you are running a QNX-hosted version of the WATCOM Linker. 
When a library file is specified in a "FILE" directive and obj_module is specified, the object module identified by obj_module is extracted from the library file and included in the executable file.  If obj_module is not specified (only the library file is specified), all object modules in the library are included in the executable file. 

major specifies the major version number. 

lbc_file is a file specification for the name of a librarian command file.  If no file extension is specified, a file extension of "lbc" is assumed. 

map_file is a file specification for the name of the map file.  If no file extension is specified, a file extension of "map" is assumed. 

minor specifies the minor version number and must be less than 100. 

module_name is the name of a dynamic link library.  Note that this need not be the same as the file name of the executable file that contains the dynamic link library. 

n represents a value.  The complete form of n is the following. 
    
   [0x]d{d}[k|m] 
d represents a decimal digit.  If 0x is specified, the string of digits represents a hexadecimal number.  If k is specified, the value is multiplied by 1024.  If m is specified, the value is multiplied by 1024*1024. 

obj_file is a file specification for the name of an object file.  If no file extension is specified, a file extension of "obj" is assumed if you are running a DOS, OS/2 or Windows NT-hosted version of the WATCOM Linker.  Also, if you are running a DOS, OS/2 or Windows NT-hosted version of the WATCOM Linker, the object file specification can contain wild cards (*, ?).  A file extension of "o" is assumed if you are running a QNX-hosted version of the WATCOM Linker. 

obj_module is the name of an object module contained in a library file or object file. 
Object files may contain multiple object modules.  A simple way of creating such an object file is to concatenate a number of object files into a single object file.  Each of the original object files is now an object module in the resulting object file.  Also, some language processors may generate object files that contain multiple object modules.  Specifying obj_module allows you to select a particular object module from an object file. 

path_name is a path name. 

msg_num is a message number. 

seg_name is the name of the code or data segment whose attributes are being specified. 

stub_name is a file specification for the name of the executable file.  If no file extension is specified, a file extension of "exe" is assumed. 

symbol_file is a file specification for the name of the symbol file.  If no file extension is specified, a file extension of "sym" is assumed. 

symbol_name is the name of a symbol. 

alias_name is the name of an alias symbol. 

system_name is the name of a system. 
You can view all the directives specific to OS/2 executable files by simply typing the following: 
    
   wlink ? os2 
Notes: 

 1.If the file "wlink.hlp" is located in one of the paths specified in the "PATH" environment variable, the contents of that file will be displayed when the following command is issued. 
    
   wlink ? 

 2.If all of the directive information does not fit on the command line, type the following. 
    
   wlink 
The prompt "WLINK>" will appear on the next line.  You can enter as many lines of directive information as required.  Press "Ctrl/Z" followed by the "Enter" key to terminate the input of directive information if you are running a DOS, OS/2 or Windows NT-hosted version of the WATCOM Linker.  Press "Ctrl/D" to terminate the input of directive information if you are running a QNX-hosted version of the WATCOM Linker.


### OS/2:  Dynamic Link Libraries

The WATCOM Linker can generate two forms of executable files; program modules and dynamic link libraries.  A program module is the executable file that gets loaded by OS/2 when you run your application.  A dynamic link library is really a library of routines that are called by a program module but not linked into the program module.  The executable code in a dynamic link library gets loaded by OS/2 during the execution of a program module when a routine in the dynamic link library is called. 
Program modules are contained in files whose name has a file extension of "exe".  Dynamic link libraries are contained in files whose name has a file extension of "dll".  The WATCOM Linker "FORMAT" directive can be used to select the type of executable file to be generated. 
Let us consider some of the advantages of using dynamic link libraries over standard libraries. 

 1.Functions in dynamic link libraries are not linked into your program.  Only references to the functions in dynamic link libraries are placed in the program module.  These references are called import definitions.  As a result, the linking time is reduced and disk space is saved.  If many applications reference the same dynamic link library, the saving in disk space can be significant. 

 2.Since program modules only reference dynamic link libraries and do not contain the actual executable code, a dynamic link library can be updated without re-linking your application.  When your application is executed, it will use the updated version of the dynamic link library. 

 3.Dynamic link libraries also allow sharing of code and data between the applications that use them.  If many applications that use the same dynamic link library are executing concurrently, the sharing of code and data segments improves memory utilization.


#### OS/2:  Creating a Dynamic Link Library

To create a dynamic link library, you must specify the following form of the "FORMAT" directive. 
    
   format os2 dll 
In addition, you must specify which functions in the dynamic link library are to be made available to applications which use it.  This is achieved by using the "EXPORT" directive for each function that can be called by an application. 
Dynamic link libraries can reference other dynamic link libraries.  References to other dynamic link libraries are resolved by specifying "IMPORT" directives or using import libraries.


#### OS/2:  Using a Dynamic Link Library

To use a dynamic link library, you must tell the WATCOM Linker which functions are contained in a dynamic link library and the name of the dynamic link library.  This is achieved in two ways. 
The first method is to use the "IMPORT" directive.  The "IMPORT" directive names the function and the dynamic link library it belongs to so that the WATCOM Linker can generate an import definition in the program module. 
The second method is to use import libraries.  An import library is a standard library which contains object modules with special object records that define the functions belonging to a dynamic link library.  An import library is created from a dynamic link library using the WATCOM Library Manager.  The resulting import library can then be specified in a "LIBRARY" directive in the same way one would specify a standard library.  See the chapter entitled "The WATCOM Library Manager" in the WATCOM Tools User's Guide for more information on creating import libraries. 
Using an import library is the preferred method of providing references to functions in dynamic link libraries.  When a dynamic link library is modified, typically the import library corresponding to the modified dynamic link library is updated to reflect the changes.  Hence, any directive file that specifies the import library in a "LIBRARY" directive need not be modified.  However, if you are using "IMPORT" directives, you may have to modify the "IMPORT" directives to reflect the changes in the dynamic link library.


### OS/2:  WATCOM Linker Directives

Directives tell the WATCOM Linker how to create your program.  For example, using directives you can tell the WATCOM Linker which object files are to be included in the program, which library files to search to resolve undefined references, and the name of the executable file. 
The file WLINK.LNK is a special linker directive file that is automatically processed by the WATCOM Linker before processing any other directives.  On a DOS, OS/2 or Windows NT-hosted system, this file should be located in one of the paths specified in the PATH environment variable.  On a QNX-hosted system, this file should be located in the /etc directory.  A default version of this file is located in the \WATCOM\BIN directory on DOS-hosted systems, the \WATCOM\BINP directory on OS/2-hosted systems, the /etc directory on QNX-hosted systems, and the \WATCOM\BINNT directory on Windows NT-hosted systems.  Note that the file WLINK.LNK includes the file WLSYSTEM.LNK which is located in the \WATCOM\BINB directory on DOS, OS/2 and Windows NT-hosted systems and the /etc directory on QNX-hosted systems. 
The files WLINK.LNK and WLSYSTEM.LNK reference the WATCOM environment variable which must be set to the directory in which you installed your software. 
It is also possible to use environment variables when specifying a directive.  For example, if the LIBDIR environment variable is defined as follows, 
    
   set libdir=\test 
then the linker directive 
    
   library %libdir%\mylib 
is equivalent to the following linker directive. 
    
   library \test\mylib 
Note that a space must precede a reference to an environment variable. 
The following sections describe those WATCOM Linker directives that are used to generate OS/2 executable files.


#### OS/2:  The ALIAS Directive

The "ALIAS" directive is used to specify an equivalent name for a symbol name.  The format of the "ALIAS" directive (short form "A") is as follows. 
    
     ALIAS alias_name=symbol_name{, alias_name=symbol_name} 

alias_name is the alias name. 

symbol_name is the symbol name to which the alias name is mapped. 
Consider the following example. 
    
   alias sine=mysine 
When the linker tries to resolve the reference to sine, it will immediately substitute the name mysine for sine and begin searching for the symbol mysine.


#### OS/2:  The EXPORT Directive

The "EXPORT" directive can be used to define the names and attributes of functions in dynamic link libraries that are to be exported.  An "EXPORT" definition must be specified for every dynamic link library function that is to be made available externally. 
The format of the "EXPORT" directive (short form "EXP") is as follows. 
    
     EXPORT export{,export} 
       or 
     EXPORT =lbc_file 
     export ::= entry_name[.ordinal][=internal_name] [RESIDENT] [iopl_words] 

entry_name is the name to be used by other applications to call the function. 

ordinal is the ordinal value of the function.  If the ordinal number is specified, other applications can reference the function by using this ordinal number. 

internal_name is the actual name of the function and should only be specified if it differs from the entry name. 

RESIDENT specifies that the function's entry name should be kept resident in memory.  This applies only if the ordinal is specified.  If no ordinal is specified, the entry name is always memory resident.  Memory resident entry names allow OS/2 to resolve calls more efficiently when the call is by entry name rather than by ordinal. 

iopl_words is required for functions that execute with I/O privilege.  iopl_words specifies that total size of the function's arguments in words.  When such a function is executed, the specified number of words is copied from the caller's stack to the I/O-privileged function's stack.  The maximum number of words allowed is 63. 

lbc_file is a file specification for the name of a librarian command file.  If no file extension is specified, a file extension of "lbc" is assumed.  The linker will process the librarian command file and look for commands to the librarian that are used to create import library entries.  These commands have the following form. 
    
   ++sym.dll_name[.export_name][.ordinal] 

sym is the name of a symbol in a dynamic link library. 

dll_name is the name of the dynamic link library that defines sym. 

ordinal is the ordinal value that can be used to identify sym instead of using the name export_name.  The default export name is sym. 

export_name is the name that an application that is linking to the dynamic link library uses to reference sym. 
All other librarian commands will be ignored. 
 Note:  By default, the WATCOM C compiler appends an underscore ('_') to all function names.  This should be considered when specifying entry_name and internal_name in an "EXPORT" directive.


#### OS/2:  The FORMAT Directive

The "FORMAT" directive is used to specify the format of the executable file that the WATCOM Linker is to generate.  The format of the "FORMAT" directive (short form "FORM") is as follows. 
    
     FORMAT form 
     form ::= DOS [COM] 
           | WINDOWS [win_dll] [MEMORY] [FONT] 
           | WINDOWS NT [TNT] [dll_attrs] 
           | OS2 [os2_type] [dll_attrs | os2_attrs] 
           | PHARLAP [EXTENDED | REX] 
           | NOVELL [NLM | LAN | DSK | NAM] 'description' 
           | QNX [FLAT] 
           | ELF [DLL] 
     dll_attrs ::= DLL [INITGLOBAL | INITINSTANCE] 
              [TERMINSTANCE | TERMGLOBAL] 
     win_attrs ::= [win_dll] [MEMORY] [FONT] 
     win_dll ::= DLL [INITGLOBAL | INITINSTANCE] 
     os2_type ::= FLAT | LE | LX 
     os2_attrs ::= PM | PMCOMPATIBLE | FULLSCREEN 
               | PHYSDEVICE | VIRTDEVICE 

DOS (short form "D") tells the WATCOM Linker to generate a DOS "EXE" file.  For more information on DOS executable file formats, see the chapter entitled DOS:  The DOS Executable File Format. 

WINDOWS tells the WATCOM Linker to generate a Windows executable file.  For more information on Windows executable file formats, see the chapter entitled Windows:  The Windows Executable and DLL File Formats. 

WINDOWS NT tells the WATCOM Linker to generate a Windows NT executable file ("PE" format).  For more information on Windows NT executable file formats, see the chapter entitled NT:  The Windows NT Executable and DLL File Formats. 

OS2 tells the WATCOM Linker to generate an OS/2 executable file format.  The name of the executable file will have extension "exe".  If "LE" is specified, an early form of the OS/2 32-bit linear executable will be generated.  This executable file format is required by Tenberry Software's DOS/4G DOS extender. 
In order to improve load time and minimize the size of the executable file, the OS/2 32-bit linear executable file format was changed.  If "LX" or "FLAT" (short form "FL") is specified, the new form of the OS/2 32-bit linear executable will be generated.  This executable file format is required by the FlashTek DOS extender and 32-bit OS/2 executables. 
If "FLAT", "LX" or "LE" is not specified, an OS/2 16-bit executable will be generated. 
If "DLL" (short form "DL") is specified, a dynamic link library will be generated in which case the name of the executable file will have extension "dll".  Note that these default extensions can be overridden by using the "NAME" directive to name the executable file. 
Specifying INITGLOBAL (short form "INITG") will cause the initialization routine to be called the first time the dynamic link library is loaded.  Specifying INITINSTANCE (short form "INITI") will cause the initialization routine to be called each time the dynamic link library is referenced by a process.  If neither "INITGLOBAL" or "INITINSTANCE" is specified, "INITGLOBAL" is assumed.  For OS/2 32-bit linear executable files, it is also possible to specify whether the initialization routine is to be called at DLL termination or not.  Specifying TERMGLOBAL (short form "TERMG") will cause the initialization routine to be called when the last instance of the dynamic link library is terminated.  Specifying TERMINSTANCE (short form "TERMI") will cause the initialization routine to be called each time an instance of the dynamic link library is terminated.  Note that the initialization routine is passed an argument indicating whether it is being called during DLL initialization or DLL termination.  If "INITINSTANCE" is used and no termination option is specified, "TERMINSTANCE" is assumed.  If "INITGLOBAL" is used and no termination option is specified, "TERMGLOBAL" is assumed. 
If "PM" is specified, a Presentation Manager application will be created.  The application uses the API provided by the Presentation Manager and must be executed in the Presentation Manager environment. 
lf "PMCOMPATIBLE" (short form "PMC") is specified, an application compatible with Presentation Manager will be created.  The application can run inside the Presentation Manager or it can run in a separate screen group.  An application can be of this type if it uses the proper subset of OS/2 video, keyboard, and mouse functions supported in the Presentation Manager applications.  This is the default. 
If "FULLSCREEN" (short form "FULL") is specified, an OS/2 full screen application will be created.  The application will run in a separate screen group from the Presentation Manager. 
If "PHYSDEVICE" (short form "PHYS") is specified, the executable file is marked as a physical device driver. 
If "VIRTDEVICE" (short form "VIRT") is specified, the executable file is marked as a virtual device driver. 

PHARLAP (short form "PHAR") tells the WATCOM Linker to generate an executable file that will run under Phar Lap's 386|DOS-Extender.  For more information on Phar Lap executable file formats, see the chapter entitled Phar Lap:  The Phar Lap Executable File Format. 

NOVELL (short form "NOV") tells the WATCOM Linker to generate a NetWare 386 executable file, more commonly called a NetWare Loadable Module (NLM).  For more information on NetWare 386 executable file formats, see the chapter entitled NetWare:  The NetWare 386 Executable File Format. 

QNX tells the WATCOM Linker to generate a QNX executable file.  For more information on QNX executable file formats, see the chapter entitled QNX:  The QNX Executable File Format. 

ELF tells the WATCOM Linker to generate an ELF format executable file. 
If no "FORMAT" directive is specified and you are running a DOS, OS/2 or Windows NT-hosted version of the WATCOM Linker, the executable file format will be selected in the following way. 

 1.If a reference to a dynamic link library is encountered, an OS/2 executable file will be generated. 

 2.If a 386 object module is encountered, an executable file that runs under Phar Lap's 386|DOS-Extender will be generated. 

 3.Otherwise, a DOS executable file will be generated. 
If no "FORMAT" directive is specified and you are running a QNX-hosted version of the WATCOM Linker, the executable file format will be selected in the following way. 

 1.If a reference to a dynamic link library is encountered, an OS/2 format executable file will be generated. 

 2.If a 386 object module is encountered, an executable file that runs under Phar Lap's 386|DOS-Extender will be generated. 

 3.Otherwise, a QNX executable file will be generated.


#### OS/2:  The IMPORT Directive

The "IMPORT" directive describes a function that belongs to a dynamic link library.  The format of the "IMPORT" directive (short form "IMP") is as follows. 
    
     IMPORT import{,import} 
     import ::= internal_name module_name[.entry_name | ordinal] 

internal_name is the name the application used to call the function. 

module_name is the name of the dynamic link library.  Note that this need not be the same as the file name of the executable file containing the dynamic link library.  This name corresponds to the name specified by the "MODNAME" option when the dynamic link library was created. 

entry_name is the actual name of the function as defined in the dynamic link library. 

ordinal is the ordinal value of the function.  The ordinal number is an alternate method that can be used to reference a function in a dynamic link library. 
 Note:  By default, the WATCOM C compiler appends an underscore ('_') to all function names.  This should be considered when specifying internal_name and entry_name in an "IMPORT" directive. 
The preferred method to resolve references to dynamic link libraries is through the use of import libraries.  See the section entitled OS/2:  Using a Dynamic Link Library for more information on import libraries.


#### OS/2:  The OPTION Directive

The "OPTION" directive is used to specify options to the WATCOM Linker.  The format of the "OPTION" directive (short form "OP") is as follows. 
    
     OPTION option{,option} 
     option ::= ALIGNMENT=n | ARTIFICIAL 
             | [NO]CACHE | [NO]CASEEXACT 
             | DESCRIPTION 'string' 
             | DOSSEG | ELIMINATE | HEAPSIZE=n 
             | INTERNALRELOCS 
             | MANGLEDNAMES | MANYAUTODATA | MAP[=map_file] 
             | MAXERRORS=n | MODNAME=module_name | NAMELEN=n 
             | NEWFILES 
             | NOAUTODATA | NODEFAULTLIBS 
             | OFFSET 
             | OLDLIBRARY=dll_name | ONEAUTODATA 
             | OSNAME='string' | PACKCODE=n | PACKDATA=n 
             | PROTMODE 
             | QUIET | REDEFSOK 
             | STACK=n | STATIC | STUB=stub_name 
             | SYMFILE[=symbol_file] | UNDEFSOK 
             | VERBOSE | VERSION=major[.minor] 

map_file is a file specification for the name of the map file.  If no file extension is specified, a file extension of "map" is assumed. 

symbol_file is a file specification for the name of the symbol file.  If no file extension is specified, a file extension of "sym" is assumed. 

module_name is the name of a program module or dynamic link library. 

dll_name is a file specification for the name of a dynamic link library.  If no file extension is specified, a file extension of "dll" is assumed. 

stub_name is a file specification for the name of the executable file.  If no file extension is specified, a file extension of "exe" is assumed. 

string is a sequence of characters. 

n represents a value.  The complete form of n is the following. 
    
   [0x]d{d}[k|m] 
d represents a decimal digit.  If 0x is specified, the string of digits represents a hexadecimal number.  If k is specified, the value is multiplied by 1024.  If m is specified, the value is multiplied by 1024*1024. 
The following sections describe the WATCOM Linker options specific to this executable format.  The options common to all executable formats are described in the chapter entitled General Directives and Options.


##### OS/2:  The ALIGNMENT Option

The "ALIGNMENT" option specifies the alignment for segments in the executable file.  The format of the "ALIGNMENT" option (short form "A") is as follows. 
    
     OPTION ALIGNMENT=n 

n represents a value.  The complete form of n is the following. 
    
   [0x]d{d}[k|m] 
d represents a decimal digit.  If 0x is specified, the string of digits represents a hexadecimal number.  If k is specified, the value is multiplied by 1024.  If m is specified, the value is multiplied by 1024*1024. 
n specifies the alignment for segments in the executable file and must be a power of 2. 
Segments in the executable file are pointed to by a segment table.  An entry in the segment table contains a 16-bit value which is a multiple of the alignment value.  Together they form the offset of the segment from the start of the segment table.  Note that the smaller the value of n the smaller the executable file. 
By default, the WATCOM Linker will automatically choose the smallest value of n possible.  You need not specify this option unless you want padding between segments in the executable file.


##### OS/2:  The DESCRIPTION Option

The "DESCRIPTION" option inserts the specified text into the application or dynamic link library.  This is useful if you wish to embed copyright information into an application or dynamic link library.  The format of the "DESCRIPTION" option (short form "DE") is as follows. 
    
     OPTION DESCRIPTION 'string' 

string is the sequence of characters to be embedded into the application or dynamic link library.


##### OS/2:  The HEAPSIZE Option

The "HEAPSIZE" option specifies the size of the heap required by the application.  The format of the "HEAPSIZE" option (short form "H") is as follows. 
    
     OPTION HEAPSIZE=n 

n represents a value.  The complete form of n is the following. 
    
   [0x]d{d}[k|m] 
d represents a decimal digit.  If 0x is specified, the string of digits represents a hexadecimal number.  If k is specified, the value is multiplied by 1024.  If m is specified, the value is multiplied by 1024*1024. 
n specifies the size of the heap.  The default heap size is 0 bytes.  The maximum value of n is 65536 (64K) for 16-bit applications and 4G for 32-bit applications which is the maximum size of a physical segment.  Actually, for a particular application, the maximum value of n is 64K or 4G less the size of group "DGROUP".


##### OS/2:  The INTERNALRELOCS Option

The "INTERNALRELOCS" option is used with LX format executables under OS/2 2.x.  By default, OS/2 executables do not contain internal relocation information and OS/2 dynamic link libraries do contain internal relocation information.  This option causes the WATCOM Linker to include internal relocation information to OS/2 LX format executables. 
The format of the "INTERNALRELOCS" option (short form "INT") is as follows. 
    
     OPTION INTERNALRELOCS


##### OS/2:  The MANYAUTODATA Option

The "MANYAUTODATA" option specifies that a copy of the automatic data segment (default data segment defined by the group "DGROUP"), for the program module or dynamic link library being created, is made for each instance.  The format of the "MANYAUTODATA" option (short form "MANY") is as follows. 
    
     OPTION MANYAUTODATA 
The default for a program module is "MANYAUTODATA" and for a dynamic link library is "ONEAUTODATA".


##### OS/2:  The MODNAME Option

The "MODNAME" option specifies a name to be given to the module being created.  The format of the "MODNAME" option (short form "MODN") is as follows. 
    
     OPTION MODNAME=module_name 

module_name is the name of a dynamic link library. 
Once a module has been loaded (whether it be a program module or a dynamic link library), mod_name is the name of the module known to OS/2.  If the "MODNAME" option is not used to specify a module name, the default module name is the name of the executable file without the file extension.


##### OS/2:  The NEWFILES Option

The "NEWFILES" option specifies that the application uses the high-performance file system.  The format of the "NEWFILES" option (short form "NEWF") is as follows. 
    
     OPTION NEWFILES


##### OS/2:  The NOAUTODATA Option

The "NOAUTODATA" option specifies that no automatic data segment (default data segment defined by the group "DGROUP"), exists for the program module or dynamic link library being created.  The format of the "NOAUTODATA" option (short form "NOA") is as follows. 
    
     OPTION NOAUTODATA


##### OS/2:  The OFFSET Option

This option is allowed only when generating an OS/2 32-bit linear executable. 
The "OFFSET" option specifies the preferred base linear address at which the executable will be loaded.  The WATCOM Linker will relocate the application for the specified base linear address so that when it is loaded by the operating system, no relocation will be required.  This decreases the load time of the application. 
If the operating system is unable to load the application at the specified base linear address, it will load it at a different location which will increase the load time since a relocation phase must be performed. 
The format of the "OFFSET" option (short form "OFF") is as follows. 
    
     OPTION OFFSET=n 

n represents a value.  The complete form of n is the following. 
    
   [0x]d{d}[k|m] 
d represents a decimal digit.  If 0x is specified, the string of digits represents a hexadecimal number.  If k is specified, the value is multiplied by 1024.  If m is specified, the value is multiplied by 1024*1024. 
n specifies the base linear address (in bytes) at which the program is loaded and must be a multiple of 64K.  The WATCOM Linker will round the value up to a multiple of 64K if it is not already a multiple of 64K.  The default base linear address is 64K.


##### OS/2:  The OLDLIBRARY Option

The "OLDLIBRARY" option is used to preserve the export ordinals for successive versions of a dynamic link library.  This ensures that any application that references functions in a dynamic link library by ordinal will continue to execute correctly.  The format of the "OLDLIBRARY" option (short form "OLD") is as follows. 
    
     OPTION OLDLIBRARY=dll_name 

dll_name is a file specification for the name of a dynamic link library.  If no file extension is specified, a file extension of "dll" is assumed. 
Only the current directory or a specified directory will be searched for dynamic link libraries specified in the "OLDLIBRARY" option.


##### OS/2:  The ONEAUTODATA Option

The "ONEAUTODATA" option specifies that the automatic data segment (default data segment defined by the group "DGROUP") for the program module or dynamic link library being created will be shared by all instances.  The format of the "ONEAUTODATA" option (short form "ONE") is as follows. 
    
     OPTION ONEAUTODATA 
The default for a dynamic link library is "ONEAUTODATA" and for a program module is "MANYAUTODATA".


##### OS/2:  The PACKDATA Option

By default, the WATCOM Linker automatically groups logical code segments into physical segments.  The "PACKDATA" option is used to specify the size of the physical segment.  The format of the "PACKCODE" option (short form "PACKD") is as follows. 
    
     OPTION PACKDATA=n 

n represents a value.  The complete form of n is the following. 
    
   [0x]d{d}[k|m] 
d represents a decimal digit.  If 0x is specified, the string of digits represents a hexadecimal number.  If k is specified, the value is multiplied by 1024.  If m is specified, the value is multiplied by 1024*1024. 
n specifies the size of the physical segments into which far data segments are packed.  The default value of n is 64K.  Note that this is also the maximum size of a physical segment.  To suppress automatic grouping of far data segments, specify a value of 0 for n. 
Notes: 

 1.Only adjacent segments are packed into a physical segment. 

 2.Segments belonging to the same group are packed in a physical segment.  Segments belonging to different groups are not packed into a physical segment. 

 3.Segments with different attributes are not packed together unless they are explicitly grouped.


##### OS/2:  The PROTMODE Option

The "PROTMODE" option specifies that the application will only run in protected mode.  The format of the "PROTMODE" option (short form "PROT") is as follows. 
    
     OPTION PROTMODE


##### OS/2:  The STUB Option

The "STUB" option specifies an executable file that is to be placed at the beginning of the OS/2 executable file being generated.  This program will be executed if the OS/2 module is executed under DOS.  The format of the "STUB" option is as follows. 
    
     OPTION STUB=stub_name 

stub_name is a file specification for the name of the stub executable file.  If no file extension is specified, a file extension of "exe" is assumed. 
The WATCOM Linker will search all paths specified in the "path" environment variable for the stub executable file.  The stub executable file specified by the "STUB" option must not be the same as the executable file being generated.


##### OS/2:  The VERSION Option

The "VERSION" option can be used to identify the application so that it can be distinguished from other versions (releases) of the same application.  This option is most useful when creating a DLL since applications that use the DLL may only execute with a specific version of the DLL. 
The format of the "VERSION" option (short form "VER") is as follows. 
    
     OPTION VERSION=major[.minor] 

major specifies the major version number. 

minor specifies the minor version number and must be less than 100.


#### OS/2:  The REFERENCE Directive

The "REFERENCE" directive is used to explicitly reference a symbol that is not referenced by any object file processed by the linker.  If any symbol appearing in a "REFERENCE" directive is not resolved by the linker, an error message will be issued for that symbol specifying that the symbol is undefined. 
The "REFERENCE" directive can be used to force object files from libraries to be linked with the application.  Also note that a symbol appearing in a "REFERENCE" directive will not be eliminated by dead code elimination.  For more information on dead code elimination, see the section entitled The ELIMINATE Option. 
The format of the "REFERENCE" directive (short form "REF") is as follows. 
    
     REFERENCE symbol_name{, symbol_name} 

symbol_name is the symbol for which a reference is made. 
Consider the following example. 
    
   reference domino 
The symbol domino will be searched for.  The object module that defines this symbol will be linked with the application.  Note that the linker will also attempt to resolve symbols referenced by this module.


#### OS/2:  The SEGMENT Directive

The "SEGMENT" directive is used to describe the attributes of code and data segments.  The format of the "SEGMENT" directive (short form "SE") is as follows. 
    
     SEGMENT seg_desc{,seg_desc} 
     seg_desc ::= seg_id {seg_attrs}+ 
     seg_id ::= 'seg_name' | CLASS 'class_name' | TYPE [CODE | DATA] 
     seg_attrs ::= PRELOAD | LOADONCALL 
               | IOPL | NOIOPL 
               | EXECUTEONLY | EXECUTEREAD 
               | READONLY | READWRITE 
               | SHARED | NONSHARED 
               | CONFORMING | NONCONFORMING 

seg_name is the name of the code or data segment whose attributes are being specified. 

class_name is a class name.  The attributes will be assigned to all segments belonging to the specified class. 

PRELOAD (short form "PR") specifies that the segment is loaded as soon as the executable file is loaded.  This is the default. 

LOADONCALL (short form "LO") specifies that the segment is loaded only when accessed. 

IOPL (short form "I") specifies that the segment requires I/O privilege.  That is, they can access the hardware directly. 

NOIOPL (short form "NOI") specifies that the segment does not require I/O privilege.  This is the default. 

EXECUTEONLY (short form "EXECUTEO") specifies that the segment can only be executed.  This attribute should only be specified for code segments.  This attribute should not be specified if it is possible for the code segment to contain jump tables which is the case with the WATCOM C and FORTRAN optimizing compilers. 

EXECUTEREAD (short form "EXECUTER") specifies that the segment can only be executed and read.  This attribute, the default for code segments, should only be specified for code segments.  This attribute is appropriate for code segments that contain jump tables as is possible with the WATCOM C and FORTRAN optimizing compilers. 

READONLY (short form "READO") specifies that the segment can only be read.  This attribute should only be specified for data segments. 

READWRITE (short form "READW") specifies that the segment can be read and written.  This is the default for data segments.  This attribute should only be specified for data segments. 

SHARED (short form "SH" ) specifies that a single copy of the segment will be loaded and will be shared by all processes. 

NONSHARED (short form "NONS") specifies that a unique copy of the segment will be loaded for each process.  This is the default. 

CONFORMING (short form "CON") specifies that the segment will assume the I/O privilege of the segment that referenced it.  By default, the segment is "NONCONFORMING". 

NONCONFORMING (short form "NONC") specifies that the segment will not assume the I/O privilege of the segment that referenced it. This is the default. 
 Note:  Attributes specified for segments identified by a segment name override attributes specified for segments identified by a class name.


#### OS/2:  The SORT Directive

The "SORT" directive is used to sort the symbols in the "Memory Map" section of the map file.  By default, symbols are listed on a per module basis in the order the modules were encountered by the linker.  That is, a module header is displayed followed by the symbols defined by the module. 
The format of the "SORT" directive (short form "SO") is as follows. 
    
     SORT [GLOBAL] [ALPHABETICAL] 
If the "SORT" directive is specified without any options, as in the following example, the module headers will be displayed each followed by the list of symbols it defines sorted by address. 
    
   sort 
If only the "GLOBAL" sort option (short form "GL") is specified, as in the following example, the module headers will not be displayed and all symbols will be sorted by address. 
    
   sort global 
If only the "ALPHABETICAL" sort option (short form "ALP") is specified, as in the following example, the module headers will be displayed each followed by the list of symbols it defines sorted alphabetically. 
    
   sort alphabetical 
If both the "GLOBAL" and "ALPHABETICAL" sort options are specified, as in the following example, the module headers will not be displayed and all symbols will be sorted alphabetically. 
    
   sort global alphabetical 
If you are linking a WATCOM C++ application, mangled names are sorted by using the base name.  The base name is the name of the symbol as it appeared in the source file.  See the section entitled The MANGLEDNAMES Option for more information on mangled names.


### OS/2:  Memory Layout

The following describes the segment ordering of an application linked by the WATCOM Linker.  Note that this assumes that the "DOSSEG" linker option has been specified. 

 1.all segments not belonging to group "DGROUP" with class "CODE" 

 2.all other segments not belonging to group "DGROUP" 

 3.all segments belonging to group "DGROUP" with class "BEGDATA" 

 4.all segments belonging to group "DGROUP" not with class "BEGDATA", "BSS" or "STACK" 

 5.all segments belonging to group "DGROUP" with class "BSS" 

 6.all segments belonging to group "DGROUP" with class "STACK" 
A special segment belonging to class "BEGDATA" is defined when linking with WATCOM run-time libraries.  This segment is initialized with the hexadecimal byte pattern "01" and is the first segment in group "DGROUP" so that storing data at location 0 can be detected. 
Segments belonging to class "BSS" contain uninitialized data.  Note that this only includes uninitialized data in segments belonging to group "DGROUP".  Segments belonging to class "STACK" are used to define the size of the stack used for your application.  Segments belonging to the classes "BSS" and "STACK" are last in the segment ordering so that uninitialized data need not take space in the executable file.


### OS/2:  The WATCOM Linker Memory Requirements

The WATCOM Linker uses all available memory when linking an application.  For DOS-hosted versions of the WATCOM Linker, this includes expanded memory (EMS) and extended memory.  It is possible for the size of the image being linked to exceed the amount of memory available in your machine, particularly if the image file is to contain debugging information. For this reason, a temporary disk file is used when all available memory is used by the WATCOM Linker. 
Normally, the temporary file is created in the default directory.  However, by defining the "tmp" environment variable to be a directory, you can tell the WATCOM Linker where to create the temporary file.  This can be particularly useful if you have a RAM disk.  Consider the following definition of the "tmp" environment variable. 
    
   set tmp=\tmp 
The WATCOM Linker will create the temporary file in the directory "\tmp".


### OS/2:  Converting Microsoft Response Files to Directive Files

A utility called MS2WLINK can be used to convert Microsoft linker response files to WATCOM Linker directive files.  Input to MS2WLINK is processed in the same way as the Microsoft linker processes its input, the difference being MS2WLINK lists the corresponding WATCOM Linker directive file to the standard output device instead of a creating an executable file.  The resulting output can be redirected to a disk file which can then be used as input to the WATCOM Linker to produce an executable file. 
Suppose you have a Microsoft linker response file called "test.rsp".  You can convert this file to a WATCOM Linker directive file by issuing the following command. 
Example: 
   ms2wlink @test.rsp >test.lnk 
You can now use the WATCOM Linker to link your program by issuing the following command. 
Example: 
   wlink @test 
An alternative way to link your application with the WATCOM Linker from a Microsoft response file is to issue the following command. 
Example: 
   ms2wlink @test.rsp | wlink 
Since the WATCOM Linker gets its input from the standard input device, you do not have to create a WATCOM Linker directive file to link your application. 
Note that MS2WLINK can also process module-definition files used for creating OS/2 applications.


## Phar Lap:  The Phar Lap Executable File Format

This chapter deals with those aspects of the WATCOM Linker required to generate Phar Lap 386|DOS-Extender executable files.  The Phar Lap executable file format will run under the following operating systems. 

 1.Phar Lap's 386|DOS-Extender 

 2.WATCOM's 32-bit Windows supervisor (relocatable format only)


### Phar Lap:  The WATCOM Linker Command Line

Input to the WATCOM Linker is specified on the command line.  The following notation is used to describe the syntax of WATCOM Linker commands. 

ABC All items in upper case are required. 

[abc] The item abc is optional. 

{abc} The item abc may be repeated zero or more times. 

{abc}+ The item abc may be repeated one or more times. 

a|b|c One of a, b or c may be specified. 

a ::= b The item a is defined in terms of b. 
The WATCOM Linker command line format is as follows. 
    
   WLINK {directive} 
where directive is any of the following: 

DEBUG [[WATCOM] db_list | CODEVIEW | DWARF] 
   db_list ::= db_option{,db_option} 
   db_option ::= LINES | TYPES | LOCALS | ALL 

| DISABLE msg_num{,msg_num} 

| FILE obj_spec{,obj_spec} 
   obj_spec ::= obj_file[(obj_module)] | library_file[(obj_module)] 

| FORMAT PHARLAP [EXTENDED | REX] 

| LIBFILE obj_file{,obj_file} 

| LIBPATH path_name{;path_name} 

| LIBRARY library_file{,library_file} 

| MODTRACE obj_module{,obj_module} 

| NAME exe_file 

| OPTION option{,option} 
   option ::=  ARTIFICIAL | [NO]CACHE | [NO]CASEEXACT | DOSSEG 
           | ELIMINATE | MANGLEDNAMES | MAP[=map_file] 
           | MAXDATA=n | MAXERRORS=n | MINDATA=n 
           | NAMELEN=n | NODEFAULTLIBS | OFFSET=n 
           | OSNAME='string' | PACKCODE=n | QUIET 
           | REDEFSOK | STACK=n | STATIC 
           | SYMFILE[=symbol_file] | UNDEFSOK | VERBOSE 

| PATH path_name{;path_name} 

| RUNTIME run_option{,run_option} 
   run_option ::= MINREAL=n | MAXREAL=n | CALLBUFS=n 
               | PRIVILEGED | MINIBUF=n | MAXIBUF=n 
               | NISTACK=n | ISTKSIZE=n 
               | REALBREAK=offset | UNPRIVILEGED 
   offset ::= n | symbol_name 

| SORT [GLOBAL] [ALPHABETICAL] 

| SYMTRACE symbol_name{,symbol_name} 

| SYSTEM BEGIN system_name {directive} END 

| SYSTEM system_name 

| # comment 

| @ directive_file 

obj_file is a file specification for the name of an object file.  If no file extension is specified, a file extension of "obj" is assumed if you are running a DOS, OS/2 or Windows NT-hosted version of the WATCOM Linker.  Also, if you are running a DOS, OS/2 or Windows NT-hosted version of the WATCOM Linker, the object file specification can contain wild cards (*, ?).  A file extension of "o" is assumed if you are running a QNX-hosted version of the WATCOM Linker. 

library_file is a file specification for the name of a library file.  If library_file appears in a "LIBRARY" directive and no file extension is specified, a file extension of "lib" is assumed.  If library_file appears in a "FILE" directive and no file extension is specified, a file extension of "obj" is assumed if you are running a DOS, OS/2 or Windows NT-hosted version of the WATCOM Linker.  A file extension of "o" is assumed if you are running a QNX-hosted version of the WATCOM Linker. 
When a library file is specified in a "FILE" directive and obj_module is specified, the object module identified by obj_module is extracted from the library file and included in the executable file.  If obj_module is not specified (only the library file is specified), all object modules in the library are included in the executable file. 

obj_module is the name of an object module contained in a library file or object file. 
Object files may contain multiple object modules.  A simple way of creating such an object file is to concatenate a number of object files into a single object file.  Each of the original object files is now an object module in the resulting object file.  Also, some language processors may generate object files that contain multiple object modules.  Specifying obj_module allows you to select a particular object module from an object file. 

exe_file is a file specification for the name of the executable file.  If no file extension is specified, a file extension of "exp" is assumed unless a relocatable executable file is being generated in which case a file extension of "rex" is assumed. 

path_name is a path name. 

msg_num is a message number. 

directive_file is a file specification for the name of a linker directive file.  If no file extension is specified, a file extension of "lnk" is assumed. 

map_file is a file specification for the name of the map file.  If no file extension is specified, a file extension of "map" is assumed. 

symbol_file is a file specification for the name of the symbol file.  If no file extension is specified, a file extension of "sym" is assumed. 

symbol_name is a symbol name. 

system_name is the name of a system. 

comment is any sequence of characters. 

n represents a value.  The complete form of n is the following. 
    
   [0x]d{d}[k|m] 
d represents a decimal digit.  If 0x is specified, the string of digits represents a hexadecimal number.  If k is specified, the value is multiplied by 1024.  If m is specified, the value is multiplied by 1024*1024. 
You can view all the directives specific to Phar Lap 386|DOS-Extender executable files by simply typing the following: 
    
   wlink ? phar 
Notes: 

 1.If the file "wlink.hlp" is located in one of the paths specified in the "PATH" environment variable, the contents of that file will be displayed when the following command is issued. 
    
   wlink ? 

 2.If all of the directive information does not fit on the command line, type the following. 
    
   wlink 
The prompt "WLINK>" will appear on the next line.  You can enter as many lines of directive information as required.  Press "Ctrl/Z" followed by the "Enter" key to terminate the input of directive information if you are running a DOS, OS/2 or Windows NT-hosted version of the WATCOM Linker.  Press "Ctrl/D" to terminate the input of directive information if you are running a QNX-hosted version of the WATCOM Linker.


### Phar Lap:  32-bit Protected-Mode Applications

The WATCOM Linker generates executable files that run under Phar Lap's 386|DOS-Extender.  386|DOS-Extender provides a 32-bit protected-mode environment for programs running under PC DOS.  Running in 32-bit protected mode allows your program to access all of the memory in your machine. 
Essentially, what 386|DOS-Extender does is provide an interface between your application and DOS running in real mode.  Whenever your program issues a software interrupt (DOS and BIOS system calls), 386|DOS-Extender intercepts the requests, transfers data between the protected-mode and real-mode address space, and calls the corresponding DOS system function running in real mode.


### Phar Lap:  Memory Usage

When running a program under 386|DOS-Extender, memory for the program is allocated from conventional memory (memory below one megabyte) and extended memory.  Conventional memory is allocated from a block of memory that is obtained from DOS by 386|DOS-Extender at initialization time.  By default, all available memory is allocated at initialization time; no conventional memory remains free.  The "MINREAL" and "MAXREAL" options of the "RUNTIME" directive control the amount of conventional memory initially left free by 386|DOS-Extender. 
Part of the conventional memory allocated at initialization is required by 386|DOS-Extender.  The following is allocated from conventional memory for use by 386|DOS-Extender. 

 1.A data buffer is allocated and is used to pass data to DOS and BIOS system functions.  The size allocated is controlled by the "MINIBUF" and "MAXIBUF" options of the "RUNTIME" directive. 

 2.Stack space is allocated and is used for switching between 32-bit protected mode and real mode.  The size allocated is controlled by the "NISTACK" and "ISTKSIZE" options of the "RUNTIME" directive. 

 3.A call buffer is allocated and is used for passing data on function calls between 32-bit protected mode and real mode.  The size allocated is controlled by the "CALLBUFS" option of the "RUNTIME" directive. 
When a program is loaded by 386|DOS-Extender, memory to hold the entire program is allocated.  In addition, memory beyond the end of the program is allocated for use by the program.  By default, all extra memory is allocated when the program is loaded.  It is assumed that any memory not required by the program is freed by the program.  The amount of memory allocated at the end of the program is controlled by the "MINDATA" and "MAXDATA" options.


### Phar Lap:  WATCOM Linker Directives

Directives tell the WATCOM Linker how to create your program.  For example, using directives you can tell the WATCOM Linker which object files are to be included in the program, which library files to search to resolve undefined references, and the name of the executable file. 
The file WLINK.LNK is a special linker directive file that is automatically processed by the WATCOM Linker before processing any other directives.  On a DOS, OS/2 or Windows NT-hosted system, this file should be located in one of the paths specified in the PATH environment variable.  On a QNX-hosted system, this file should be located in the /etc directory.  A default version of this file is located in the \WATCOM\BIN directory on DOS-hosted systems, the \WATCOM\BINP directory on OS/2-hosted systems, the /etc directory on QNX-hosted systems, and the \WATCOM\BINNT directory on Windows NT-hosted systems.  Note that the file WLINK.LNK includes the file WLSYSTEM.LNK which is located in the \WATCOM\BINB directory on DOS, OS/2 and Windows NT-hosted systems and the /etc directory on QNX-hosted systems. 
The files WLINK.LNK and WLSYSTEM.LNK reference the WATCOM environment variable which must be set to the directory in which you installed your software. 
It is also possible to use environment variables when specifying a directive.  For example, if the LIBDIR environment variable is defined as follows, 
    
   set libdir=\test 
then the linker directive 
    
   library %libdir%\mylib 
is equivalent to the following linker directive. 
    
   library \test\mylib 
Note that a space must precede a reference to an environment variable. 
The following sections describe those WATCOM Linker directives that are used to generate Phar Lap 386|DOS-Extender executable files.


#### Phar Lap:  The FORMAT Directive

The "FORMAT" directive is used to specify the format of the executable file that the WATCOM Linker is to generate.  The format of the "FORMAT" directive (short form "FORM") is as follows. 
    
     FORMAT form 
     form ::= DOS [COM] 
           | WINDOWS [win_dll] [MEMORY] [FONT] 
           | WINDOWS NT [TNT] [dll_attrs] 
           | OS2 [os2_type] [dll_attrs | os2_attrs] 
           | PHARLAP [EXTENDED | REX] 
           | NOVELL [NLM | LAN | DSK | NAM] 'description' 
           | QNX [FLAT] 
           | ELF [DLL] 
     dll_attrs ::= DLL [INITGLOBAL | INITINSTANCE] 
              [TERMINSTANCE | TERMGLOBAL] 
     win_attrs ::= [win_dll] [MEMORY] [FONT] 
     win_dll ::= DLL [INITGLOBAL | INITINSTANCE] 
     os2_type ::= FLAT | LE | LX 
     os2_attrs ::= PM | PMCOMPATIBLE | FULLSCREEN 
               | PHYSDEVICE | VIRTDEVICE 

DOS (short form "D") tells the WATCOM Linker to generate a DOS "EXE" file.  For more information on DOS executable file formats, see the chapter entitled DOS:  The DOS Executable File Format. 

WINDOWS tells the WATCOM Linker to generate a Windows executable file.  For more information on Windows executable file formats, see the chapter entitled Windows:  The Windows Executable and DLL File Formats. 

WINDOWS NT tells the WATCOM Linker to generate a Windows NT executable file ("PE" format).  For more information on Windows NT executable file formats, see the chapter entitled NT:  The Windows NT Executable and DLL File Formats. 

OS2 tells the WATCOM Linker to generate an OS/2 executable file format.  For more information on OS/2 executable file formats, see the chapter entitled OS/2:  The OS/2 Executable and DLL File Formats. 

PHARLAP (short form "PHAR") tells the WATCOM Linker to generate an executable file that will run under Phar Lap's 386|DOS-Extender.  There are 3 forms of executable files:  simple, extended and relocatable.  If "EXTENDED" (short form "EXT") is specified, an extended form of the executable file with file extension "exp" will be generated.  If "REX" is specified, a relocatable executable file with file extension "rex" will be generated.  If neither "EXTENDED" nor "REX" is specified, a simple executable file with file extension "exp" will be generated.  Note that the default file extensions can be overridden by using the "NAME" directive to name the executable file. 
The simple form is for flat model 386 applications.  It is the only format that can be loaded by earlier versions of 386|DOS-Extender (earlier than 1.2). 
The extended form is used for flat model applications that have been linked in a way which requires a method of specifying more information for 386|DOS-Extender than possible with the simple form. 
The relocatable form is similar to the simple form.  Unique to the relocatable form is an offset relocation table.  This allows the loader to load the program at any location it chooses. 
A simple form of the executable file is generated in all but the following cases. 

 1."EXTENDED" is specified in the "FORMAT" directive. 

 2.The "RUNTIME" directive is specified.  Options specified by the "RUNTIME" directive can only be specified in the extended form of the executable file. 

 3.The "OFFSET" option is specified.  The value specified in the "OFFSET" option can only be specified in the extended form of the executable file. 

 4."REX" is specified in the "FORMAT" directive.  In this case, the relocatable form will be generated.  You must not specify the "RUNTIME" directive or the "OFFSET" option when generating the relocatable form. 

NOVELL (short form "NOV") tells the WATCOM Linker to generate a NetWare 386 executable file, more commonly called a NetWare Loadable Module (NLM).  For more information on NetWare 386 executable file formats, see the chapter entitled NetWare:  The NetWare 386 Executable File Format. 

QNX tells the WATCOM Linker to generate a QNX executable file.  For more information on QNX executable file formats, see the chapter entitled QNX:  The QNX Executable File Format. 

ELF tells the WATCOM Linker to generate an ELF format executable file. 
If no "FORMAT" directive is specified and you are running a DOS, OS/2 or Windows NT-hosted version of the WATCOM Linker, the executable file format will be selected in the following way. 

 1.If a reference to a dynamic link library is encountered, an OS/2 executable file will be generated. 

 2.If a 386 object module is encountered, an executable file that runs under Phar Lap's 386|DOS-Extender will be generated. 

 3.Otherwise, a DOS executable file will be generated. 
If no "FORMAT" directive is specified and you are running a QNX-hosted version of the WATCOM Linker, the executable file format will be selected in the following way. 

 1.If a reference to a dynamic link library is encountered, an OS/2 format executable file will be generated. 

 2.If a 386 object module is encountered, an executable file that runs under Phar Lap's 386|DOS-Extender will be generated. 

 3.Otherwise, a QNX executable file will be generated.


#### Phar Lap:  The OPTION Directive

The "OPTION" directive is used to specify options to the WATCOM Linker.  The format of the "OPTION" directive (short form "OP") is as follows. 
    
     OPTION option{,option} 
     option ::=  ARTIFICIAL | [NO]CACHE | [NO]CASEEXACT | DOSSEG 
             | ELIMINATE | MANGLEDNAMES | MAP[=map_file] 
             | MAXDATA=n | MAXERRORS=n | MINDATA=n 
             | NAMELEN=n | NODEFAULTLIBS | OFFSET=n 
             | OSNAME='string' | PACKCODE=n | QUIET 
             | REDEFSOK | STACK=n | STATIC 
             | SYMFILE[=symbol_file] | UNDEFSOK | VERBOSE 

map_file is a file specification for the name of the map file.  If no file extension is specified, a file extension of "map" is assumed. 

symbol_file is a file specification for the name of the symbol file.  If no file extension is specified, a file extension of "sym" is assumed. 

n represents a value.  The complete form of n is the following. 
    
   [0x]d{d}[k|m] 
d represents a decimal digit.  If 0x is specified, the string of digits represents a hexadecimal number.  If k is specified, the value is multiplied by 1024.  If m is specified, the value is multiplied by 1024*1024. 
The following sections describe the WATCOM Linker options specific to this executable format.  The options common to all executable formats are described in the chapter entitled General Directives and Options.


##### Phar Lap:  The MAXDATA Option

The format of the "MAXDATA" option (short form "MAXD") is as follows. 
    
     OPTION MAXDATA=n 

n represents a value.  The complete form of n is the following. 
    
   [0x]d{d}[k|m] 
d represents a decimal digit.  If 0x is specified, the string of digits represents a hexadecimal number.  If k is specified, the value is multiplied by 1024.  If m is specified, the value is multiplied by 1024*1024. 
n specifies the maximum number of bytes, in addition to the memory required by executable image, that may be allocated by 386|DOS-Extender at the end of the loaded executable image.  No more than n bytes will be allocated. 
If the "MAXDATA" option is not specified, a default value of hexadecimal ffffffff is assumed.  This means that 386|DOS-Extender will allocate all available memory to the program at load time.


##### Phar Lap:  The MINDATA Option

The format of the "MINDATA" option (short form "MIND") is as follows. 
    
     OPTION MINDATA=n 

n represents a value.  The complete form of n is the following. 
    
   [0x]d{d}[k|m] 
d represents a decimal digit.  If 0x is specified, the string of digits represents a hexadecimal number.  If k is specified, the value is multiplied by 1024.  If m is specified, the value is multiplied by 1024*1024. 
n specifies the minimum number of bytes, in addition to the memory required by executable image, that must be allocated by 386|DOS-Extender at the end of the loaded executable image.  If n bytes are not available, the program will not be executed. 
If the "MINDATA" option is not specified, a default value of zero is assumed.  This means that 386|DOS-Extender will load the program as long as there is enough memory for the load image; no extra memory is required.


##### Phar Lap:  The OFFSET Option

The "OFFSET" option specifies the offset in the program's segment in which the first byte of code or data is loaded.  The format of the "OFFSET" option (short form "OFF") is as follows. 
    
     OPTION OFFSET=n 

n represents a value.  The complete form of n is the following. 
    
   [0x]d{d}[k|m] 
d represents a decimal digit.  If 0x is specified, the string of digits represents a hexadecimal number.  If k is specified, the value is multiplied by 1024.  If m is specified, the value is multiplied by 1024*1024. 
n specifies the offset (in bytes) at which the program is loaded and must be a multiple of 4K.  The WATCOM Linker will round the value up to a multiple of 4K if it is not already a multiple of 4K. 
 Note:  It is possible to detect NULL pointer references by linking the program at an offset which is a multiple of 4K.  Usually an offset of 4K is sufficient. 
 option offset=4k                               
               
 When the program is loaded by 386|DOS-Extender, the pages skipped by the "OFFSET" option are not mapped.  Any reference to an unmapped area (such as a NULL pointer) will cause a page fault preventing the NULL reference from corrupting the program.


#### Phar Lap:  The RUNTIME Directive

The "RUNTIME" directive describes information that is used by 386|DOS-Extender to setup the environment for execution of the program.  The format of the "RUNTIME" directive (short form "RU") is as follows. 
    
     RUNTIME run_option{,run_option} 
     run_option ::= MINREAL=n | MAXREAL=n | CALLBUFS=n | MINIBuf=n 
                | MAXIBUF=n | NISTACK=n | ISTKSIZE=n 
                | REALBREAK=offset | PRIVILEGED | UNPRIVILEGED 
     offset ::= n | symbol_name 

n represents a value.  The complete form of n is the following. 
    
   [0x]d{d}[k|m] 
d represents a decimal digit.  If 0x is specified, the string of digits represents a hexadecimal number.  If k is specified, the value is multiplied by 1024.  If m is specified, the value is multiplied by 1024*1024. 

symbol_name is a symbol name. 

MINREAL (short form "MINR") specifies the minimum number of bytes of conventional memory required to be free after a program is loaded by 386|DOS-Extender.  Note that this memory is no longer available to the executing program.  The default value of n is 0 in which case 386|DOS-Extender allocates all conventional memory for the executing program.  The WATCOM Linker truncates the specified value to a multiple of 16.  n must be less than or equal to hexadecimal 100000 (64K*16). 

MAXREAL (short form "MAXR") specifies the maximum number of bytes of conventional memory than can be left free after a program is loaded by 386|DOS-Extender.  Note that this memory is not available to the executing program.  The default value of n is 0 in which case 386|DOS-Extender allocates all conventional memory for the executing program.  n must be less than or equal to hexadecimal ffff0.  The WATCOM Linker truncates the specified value to a multiple of 16. 

CALLBUFS (short form "CALLB") specifies the size of the call buffer allocated for switching between 32-bit protected mode and real mode.  This buffer is used for communicating information between real-mode and 32-bit protected-mode procedures.  The buffer address is obtained at run-time with a 386|DOS-Extender system call.  The size returned is the size of the buffer in kilobytes and is less than or equal to 64. 
The default buffer size is zero unless changed using the "CALLBUFS" option.  The WATCOM Linker truncates the specified value to a multiple of 1024.  n must be less than or equal to 64k.  Note that n is the number of bytes, not kilobytes. 

MINIBUF (short form "MINIB") specifies the minimum size of the data buffer that is used when DOS and BIOS functions are called.  The size of this buffer is particularly important for file I/O.  If your program reads or writes large amounts of data, a large value of n should be specified.  n represents the number of bytes and must be less than or equal to 64k.  The default value of n is 1K.  The WATCOM Linker truncates the specified value to a multiple of 1024. 

MAXIBUF (short form "MAXIB") specifies the maximum size of the data buffer that is used when DOS and BIOS functions are called.  The size of this buffer is particularly important for file I/O.  If your program reads or writes large amounts of data, a large value of n should be specified.  n represents the number of bytes and must be less than or equal to 64k.  The default value of n is 4K.  The WATCOM Linker truncates the specified value to a multiple of 1024. 

NISTACK (short form "NIST") specifies the number of stack buffers to be allocated for use by 386|DOS-Extender when switching from 32-bit protected mode to real mode.  By default, 4 stack buffers are allocated.  n must be greater than or equal to 4. 

ISTKSIZE (short form "ISTK") specifies the size of the stack buffers allocated for use by 386|DOS-Extender when switching from 32-bit protected mode to real mode.  By default, the size of a stack buffer is 1k.  The value of n must be greater than or equal to 1 and less than or equal to 64k.  The WATCOM Linker truncates the specified value to a multiple of 1024. 

REALBREAK (short form "REALB") specifies how much of the program must be loaded into conventional memory so that it can be accessed and/or executed in real mode.  If n is specified, the first n bytes of the program must be loaded into conventional memory.  If symbol is specified, all bytes up to but not including the symbol must be loaded into conventional memory. 

PRIVILEGED (short form "PRIV") specifies that the executable is to run at Ring 0 privilege level. 

UNPRIVILEGED (short form "UNPRIV") specifies that the executable is to run at Ring 3 privilege level (i.e., unprivileged).  This is the default privilege level.


### Phar Lap:  Memory Layout

The following describes the segment ordering of an application linked by the WATCOM Linker.  Note that this assumes that the "DOSSEG" linker option has been specified. 

 1.all "USE16" segments.  These segments are present in applications that execute in both real mode and protected mode.  They are first in the segment ordering so that the "REALBREAK" option of the "RUNTIME" directive can be used to separate the real-mode part of the application from the protected-mode part of the application.  Currently, the "RUNTIME" directive is valid for Phar Lap executables only. 

 2.all segments not belonging to group "DGROUP" with class "CODE" 

 3.all other segments not belonging to group "DGROUP" 

 4.all segments belonging to group "DGROUP" with class "BEGDATA" 

 5.all segments belonging to group "DGROUP" not with class "BEGDATA", "BSS" or "STACK" 

 6.all segments belonging to group "DGROUP" with class "BSS" 

 7.all segments belonging to group "DGROUP" with class "STACK" 
Segments belonging to class "BSS" contain uninitialized data.  Note that this only includes uninitialized data in segments belonging to group "DGROUP".  Segments belonging to class "STACK" are used to define the size of the stack used for your application.  Segments belonging to the classes "BSS" and "STACK" are last in the segment ordering so that uninitialized data need not take space in the executable file.


### Phar Lap:  The WATCOM Linker Memory Requirements

The WATCOM Linker uses all available memory when linking an application.  For DOS-hosted versions of the WATCOM Linker, this includes expanded memory (EMS) and extended memory.  It is possible for the size of the image being linked to exceed the amount of memory available in your machine, particularly if the image file is to contain debugging information. For this reason, a temporary disk file is used when all available memory is used by the WATCOM Linker. 
Normally, the temporary file is created in the default directory.  However, by defining the "tmp" environment variable to be a directory, you can tell the WATCOM Linker where to create the temporary file.  This can be particularly useful if you have a RAM disk.  Consider the following definition of the "tmp" environment variable. 
    
   set tmp=\tmp 
The WATCOM Linker will create the temporary file in the directory "\tmp".


## QNX:  The QNX Executable File Format

This chapter deals with those aspects of the WATCOM Linker required to generate QNX executable files.  The QNX executable file format will only run under the QNX operating system.


### QNX:  The WATCOM Linker Command Line

Input to the WATCOM Linker is specified on the command line.  The following notation is used to describe the syntax of WATCOM Linker commands. 

ABC All items in upper case are required. 

[abc] The item abc is optional. 

{abc} The item abc may be repeated zero or more times. 

{abc}+ The item abc may be repeated one or more times. 

a|b|c One of a, b or c may be specified. 

a ::= b The item a is defined in terms of b. 
The WATCOM Linker command line format is as follows. 
    
   wlink {directive} 
where directive is any of the following: 

ALIAS symbol_name=symbol_name{,symbol_name=symbol_name} 

| DEBUG [[WATCOM] db_list | CODEVIEW | DWARF] 
   db_list ::= [db_option{,db_option}] 
   db_option ::= LINES | TYPES | LOCALS | STATIC | ALL 

| DISABLE msg_num{,msg_num} 

| FILE obj_spec{,obj_spec} 
   obj_spec ::= obj_file[(obj_module)] | library_file[(obj_module)] 

| FORMAT QNX [FLAT] 

| LIBFILE obj_file{,obj_file} 

| LIBPATH path_name{:path_name} 

| LIBRARY library_file{,library_file} 

| MODTRACE obj_spec{,obj_spec} 

| NAME exe_file 

| NEWSEGMENT 

| OPTION option{,option} 
   option ::= ARTIFICIAL | [NO]CACHE | [NO]CASEEXACT | DOSSEG 
           | ELIMINATE | HEAPSIZE=n | LINEARRELOCS 
           | LONGLIVED | MANGLEDNAMES | MAP[=map_file] 
           | MAXERRORS=n | NAMELEN=n | NODEFAULTLIBS 
           | NORELOCS | OFFSET=n | OSNAME='string' 
           | PACKCODE=n | PACKDATA=n | PRIVILEGE=n 
           | QUIET | REDEFSOK 
           | RESOURCE[=resource_file | 'string'] 
           | STACK=n | STATIC | SYMFILE[=symbol_file] 
           | UNDEFSOK | VERBOSE 

| PATH path_name{:path_name} 

| REFERENCE symbol_name{,symbol_name} 

| SEGMENT seg_desc{,seg_desc} 
   seg_desc ::= seg_id {seg_attrs}+ 
   seg_id ::= 'seg_name' | CLASS 'class_name' | TYPE [CODE | DATA] 
   seg_attrs ::= EXECUTEONLY | EXECUTEREAD 
             | READONLY | READWRITE 

| SORT [GLOBAL] [ALPHABETICAL] 

| SYMTRACE symbol_name{,symbol_name} 

| SYSTEM BEGIN system_name {directive} END 

| SYSTEM system_name 

| # comment 

| @ directive_file 

obj_file is a file specification for the name of an object file.  If no file extension is specified, a file extension of "obj" is assumed if you are running a DOS, OS/2 or Windows NT-hosted version of the WATCOM Linker.  Also, if you are running a DOS, OS/2 or Windows NT-hosted version of the WATCOM Linker, the object file specification can contain wild cards (*, ?).  A file extension of "o" is assumed if you are running a QNX-hosted version of the WATCOM Linker. 

library_file is a file specification for the name of a library file.  If library_file appears in a "LIBRARY" directive and no file extension is specified, a file extension of "lib" is assumed.  If library_file appears in a "FILE" directive and no file extension is specified, a file extension of "obj" is assumed if you are running a DOS, OS/2 or Windows NT-hosted version of the WATCOM Linker.  A file extension of "o" is assumed if you are running a QNX-hosted version of the WATCOM Linker. 
When a library file is specified in a "FILE" directive and obj_module is specified, the object module identified by obj_module is extracted from the library file and included in the executable file.  If obj_module is not specified (only the library file is specified), all object modules in the library are included in the executable file. 

obj_module is the name of an object module contained in a library file or object file. 
Object files may contain multiple object modules.  A simple way of creating such an object file is to concatenate a number of object files into a single object file.  Each of the original object files is now an object module in the resulting object file.  Also, some language processors may generate object files that contain multiple object modules.  Specifying obj_module allows you to select a particular object module from an object file. 

exe_file is a file specification for the name of the executable file.  If no file extension is specified, a file extension of "qnx" is assumed if you are running a DOS, OS/2 or Windows NT-hosted version of the WATCOM Linker.  No file extension is assumed if you are running a QNX-hosted version of the WATCOM Linker. 

path_name is a path name. 

msg_num is a message number. 

directive_file is a file specification for the name of a linker directive file.  If no file extension is specified, a file extension of "lnk" is assumed. 

map_file is a file specification for the name of the map file.  If no file extension is specified, a file extension of "map" is assumed. 

symbol_file is a file specification for the name of the symbol file.  If no file extension is specified, a file extension of "sym" is assumed. 

symbol_name is the name of a symbol. 

alias_name is the name of an alias symbol. 

system_name is the name of a system. 

comment is any sequence of characters. 

n represents a value.  The complete form of n is the following. 
    
   [0x]d{d}[k|m] 
d represents a decimal digit.  If 0x is specified, the string of digits represents a hexadecimal number.  If k is specified, the value is multiplied by 1024.  If m is specified, the value is multiplied by 1024*1024. 
You can view all the directives specific to QNX executable files by simply typing the following: 
    
   wlink ? qnx 
Notes: 

 1.If the file /etc/wlink.hlp exists, the contents of that file will be displayed when the following command is issued. 
    
   wlink ? 

 2.If all of the directive information does not fit on the command line, type the following. 
    
   wlink 
The prompt "WLINK>" will appear on the next line.  You can enter as many lines of directive information as required.  Press "Ctrl/Z" followed by the "Enter" key to terminate the input of directive information if you are running a DOS, OS/2 or Windows NT-hosted version of the WATCOM Linker.  Press "Ctrl/D" to terminate the input of directive information if you are running a QNX-hosted version of the WATCOM Linker.


### QNX:  WATCOM Linker Directives

Directives tell the WATCOM Linker how to create your program.  For example, using directives you can tell the WATCOM Linker which object files are to be included in the program, which library files to search to resolve undefined references, and the name of the executable file. 
The file WLINK.LNK is a special linker directive file that is automatically processed by the WATCOM Linker before processing any other directives.  On a DOS, OS/2 or Windows NT-hosted system, this file should be located in one of the paths specified in the PATH environment variable.  On a QNX-hosted system, this file should be located in the /etc directory.  A default version of this file is located in the \WATCOM\BIN directory on DOS-hosted systems, the \WATCOM\BINP directory on OS/2-hosted systems, the /etc directory on QNX-hosted systems, and the \WATCOM\BINNT directory on Windows NT-hosted systems.  Note that the file WLINK.LNK includes the file WLSYSTEM.LNK which is located in the \WATCOM\BINB directory on DOS, OS/2 and Windows NT-hosted systems and the /etc directory on QNX-hosted systems. 
The files WLINK.LNK and WLSYSTEM.LNK reference the WATCOM environment variable which must be set to the directory in which you installed your software. 
It is also possible to use environment variables when specifying a directive.  For example, if the LIBDIR environment variable is defined as follows, 
    
   export libdir=/test 
then the linker directive 
    
   library $libdir/mylib 
is equivalent to the following linker directive. 
    
   library /test/mylib 
Note that a space must precede a reference to an environment variable. 
The following sections describe those WATCOM Linker directives that are used to generate QNX executable files.


#### QNX:  The ALIAS Directive

The "ALIAS" directive is used to specify an equivalent name for a symbol name.  The format of the "ALIAS" directive (short form "A") is as follows. 
    
     ALIAS alias_name=symbol_name{, alias_name=symbol_name} 

alias_name is the alias name. 

symbol_name is the symbol name to which the alias name is mapped. 
Consider the following example. 
    
   alias sine=mysine 
When the linker tries to resolve the reference to sine, it will immediately substitute the name mysine for sine and begin searching for the symbol mysine.


#### QNX:  The FORMAT Directive

The "FORMAT" directive is used to specify the format of the executable file that the WATCOM Linker is to generate.  The format of the "FORMAT" directive (short form "FORM") is as follows. 
    
     FORMAT form 
     form ::= DOS [COM] 
           | WINDOWS [win_dll] [MEMORY] [FONT] 
           | WINDOWS NT [TNT] [dll_attrs] 
           | OS2 [os2_type] [dll_attrs | os2_attrs] 
           | PHARLAP [EXTENDED | REX] 
           | NOVELL [NLM | LAN | DSK | NAM] 'description' 
           | QNX [FLAT] 
           | ELF [DLL] 
     dll_attrs ::= DLL [INITGLOBAL | INITINSTANCE] 
              [TERMINSTANCE | TERMGLOBAL] 
     win_attrs ::= [win_dll] [MEMORY] [FONT] 
     win_dll ::= DLL [INITGLOBAL | INITINSTANCE] 
     os2_type ::= FLAT | LE | LX 
     os2_attrs ::= PM | PMCOMPATIBLE | FULLSCREEN 
               | PHYSDEVICE | VIRTDEVICE 

DOS (short form "D") tells the WATCOM Linker to generate a DOS "EXE" file.  For more information on DOS executable file formats, see the chapter entitled DOS:  The DOS Executable File Format. 

WINDOWS tells the WATCOM Linker to generate a Windows executable file.  For more information on Windows executable file formats, see the chapter entitled Windows:  The Windows Executable and DLL File Formats. 

WINDOWS NT tells the WATCOM Linker to generate a Windows NT executable file ("PE" format).  For more information on Windows NT executable file formats, see the chapter entitled NT:  The Windows NT Executable and DLL File Formats. 

OS2 tells the WATCOM Linker to generate an OS/2 executable file format.  For more information on OS/2 executable file formats, see the chapter entitled OS/2:  The OS/2 Executable and DLL File Formats. 

PHARLAP (short form "PHAR") tells the WATCOM Linker to generate an executable file that will run under Phar Lap's 386|DOS-Extender.  For more information on Phar Lap executable file formats, see the chapter entitled Phar Lap:  The Phar Lap Executable File Format. 

NOVELL (short form "NOV") tells the WATCOM Linker to generate a NetWare 386 executable file, more commonly called a NetWare Loadable Module (NLM).  For more information on NetWare 386 executable file formats, see the chapter entitled NetWare:  The NetWare 386 Executable File Format. 

QNX tells the WATCOM Linker to generate a QNX executable file.  The name of the executable file will have extension "qnx" if you are running a DOS, OS/2 or Windows NT-hosted version of the WATCOM Linker.  Note that this default extension can be overridden by using the "NAME" directive to name the executable file.  If you are running a QNX-hosted version of the WATCOM Linker, no file extension is added to the executable file name. 

ELF tells the WATCOM Linker to generate an ELF format executable file. 
If no "FORMAT" directive is specified and you are running a DOS, OS/2 or Windows NT-hosted version of the WATCOM Linker, the executable file format will be selected in the following way. 

 1.If a reference to a dynamic link library is encountered, an OS/2 executable file will be generated. 

 2.If a 386 object module is encountered, an executable file that runs under Phar Lap's 386|DOS-Extender will be generated. 

 3.Otherwise, a DOS executable file will be generated. 
If no "FORMAT" directive is specified and you are running a QNX-hosted version of the WATCOM Linker, the executable file format will be selected in the following way. 

 1.If a reference to a dynamic link library is encountered, an OS/2 format executable file will be generated. 

 2.If a 386 object module is encountered, an executable file that runs under Phar Lap's 386|DOS-Extender will be generated. 

 3.Otherwise, a QNX executable file will be generated.


#### QNX:  The OPTION Directive

The "OPTION" directive is used to specify options to the WATCOM Linker.  The format of the "OPTION" directive (short form "OP") is as follows. 
    
     OPTION option{,option} 
     option ::= ARTIFICIAL | [NO]CACHE | [NO]CASEEXACT | DOSSEG 
             | ELIMINATE | HEAPSIZE=n | LINEARRELOCS 
             | LONGLIVED | MANGLEDNAMES | MAP[=map_file] 
             | MAXERRORS=n | NAMELEN=n | NODEFAULTLIBS 
             | NORELOCS | OFFSET=n | OSNAME='string' 
             | PACKCODE=n | PACKDATA=n | PRIVILEGE=n 
             | QUIET | REDEFSOK 
             | RESOURCE[=resource_file | 'string'] 
             | STACK=n | STATIC | SYMFILE[=symbol_file] 
             | UNDEFSOK | VERBOSE 

map_file is a file specification for the name of the map file.  If no file extension is specified, a file extension of "map" is assumed. 

symbol_file is a file specification for the name of the symbol file.  If no file extension is specified, a file extension of "sym" is assumed. 

resource_file is a file specification for the name of the resource file.  No file extension is assumed. 

n represents a value.  The complete form of n is the following. 
    
   [0x]d{d}[k|m] 
d represents a decimal digit.  If 0x is specified, the string of digits represents a hexadecimal number.  If k is specified, the value is multiplied by 1024.  If m is specified, the value is multiplied by 1024*1024. 
The following sections describe the WATCOM Linker options specific to this executable format.  The options common to all executable formats are described in the chapter entitled General Directives and Options.


##### QNX:  The HEAPSIZE Option

The "HEAPSIZE" option specifies the size of the heap required by the application.  The format of the "HEAPSIZE" option (short form "H") is as follows. 
    
     OPTION HEAPSIZE=n 

n represents a value.  The complete form of n is the following. 
    
   [0x]d{d}[k|m] 
d represents a decimal digit.  If 0x is specified, the string of digits represents a hexadecimal number.  If k is specified, the value is multiplied by 1024.  If m is specified, the value is multiplied by 1024*1024. 
n specifies the size of the heap.  The default heap size is 0 bytes.  The maximum value of n is 65536 (64K) for 16-bit applications and 4G for 32-bit applications which is the maximum size of a physical segment.  Actually, for a particular application, the maximum value of n is 64K or 4G less the size of group "DGROUP".


##### QNX:  The LINEARRELOCS Option

The "LINEARRELOCS" option instructs the linker to generate offset fixups in addition to the normal segment fixups.  The offset fixups allow the system to move pieces of code and data that were loaded at a particular offset within a segment to another offset within the same segment. 
The format of the "LINEARRELOCS" option (short form "LI") is as follows. 
    
     OPTION LINEARRELOCS


##### QNX:  The LONGLIVED Option

The "LONGLIVED" option specifies that the application being linked will reside in memory, or be active, for a long period of time (e.g., background tasks).  The memory manager, knowing an application is "LONGLIVED", allocates memory for the application so as to reduce fragmentation. 
The format of the "LONGLIVED" option (short form "LO") is as follows. 
    
     OPTION LONGLIVED


##### QNX:  The NORELOCS Option

The "NORELOCS" option specifies that no relocation information is to be written to the executable file.  When the "NORELOCS" option is specified, the executable file can only be run in protected mode and will not run in real mode.  In real mode, the relocation information is required; in protected mode, the relocation information is not required unless your application is running at privilege level 0. 
The format of the "NORELOCS" option (short form "NOR") is as follows. 
    
     OPTION NORELOCS 

NORELOCS tells the WATCOM Linker not to generate relocation information.


##### QNX:  The OFFSET Option

The "OFFSET" option specifies the offset in the program's segment in which the first byte of code or data is loaded.  The format of the "OFFSET" option (short form "OFF") is as follows. 
    
     OPTION OFFSET=n 

n represents a value.  The complete form of n is the following. 
    
   [0x]d{d}[k|m] 
d represents a decimal digit.  If 0x is specified, the string of digits represents a hexadecimal number.  If k is specified, the value is multiplied by 1024.  If m is specified, the value is multiplied by 1024*1024. 
n specifies the offset (in bytes) at which the program is loaded and must be a multiple of 4K.  The WATCOM Linker will round the value up to a multiple of 4K if it is not already a multiple of 4K.  The following describes a use of the "OFFSET" option. 
 Note:  It is possible to detect NULL pointer references by linking the program at an offset which is a multiple of 4K.  Usually an offset of 4K is sufficient. 
 option offset=4k                               
               
 When the program is loaded, the pages skipped by the "OFFSET" option are not mapped.  Any reference to an unmapped area (such as a NULL pointer) will cause a page fault preventing the NULL reference from corrupting the program.


##### QNX:  The PACKDATA Option

By default, the WATCOM Linker automatically groups logical code segments into physical segments.  The "PACKDATA" option is used to specify the size of the physical segment.  The format of the "PACKCODE" option (short form "PACKD") is as follows. 
    
     OPTION PACKDATA=n 

n represents a value.  The complete form of n is the following. 
    
   [0x]d{d}[k|m] 
d represents a decimal digit.  If 0x is specified, the string of digits represents a hexadecimal number.  If k is specified, the value is multiplied by 1024.  If m is specified, the value is multiplied by 1024*1024. 
n specifies the size of the physical segments into which far data segments are packed.  The default value of n is 64K.  Note that this is also the maximum size of a physical segment.  To suppress automatic grouping of far data segments, specify a value of 0 for n. 
Notes: 

 1.Only adjacent segments are packed into a physical segment. 

 2.Segments belonging to the same group are packed in a physical segment.  Segments belonging to different groups are not packed into a physical segment. 

 3.Segments with different attributes are not packed together unless they are explicitly grouped.


##### QNX:  The PRIVILEGE Option

The "PRIVILEGE" option specifies the privilege level (0, 1, 2 or 3) at which the application will run.  The format of the "PRIVILEGE" option (short form "PRIV") is as follows. 
    
     OPTION PRIVILEGE=n 

n represents a value.  The complete form of n is the following. 
    
   [0x]d{d}[k|m] 
d represents a decimal digit.  If 0x is specified, the string of digits represents a hexadecimal number.  If k is specified, the value is multiplied by 1024.  If m is specified, the value is multiplied by 1024*1024. 
The default privilege level is 0.


##### QNX:  The RESOURCE Option

The "RESOURCE" option specifies the contents of the resource record in QNX executable files.  The format of the "RESOURCE" option (short form "RES") is as follows. 
    
     OPTION RESOURCE resource_info 
     resource_info ::= 'string' | =resource_file 

resource_file is a file specification for the name of the resource file.  No file extension is assumed. 

string is a sequence of characters which is placed in the resource record. 
If a resource file is specified, the contents of the resource file are included in the resource record. 
The resource record contains, for example, help information and is displayed when the following command is executed. 
    
   use <executable> 
QNX also provides the usemsg utility to manipulate the resource record of an executable file.  Its use is recommended.  This utility is described in the QNX "Utilities Reference" manual.


#### QNX:  The REFERENCE Directive

The "REFERENCE" directive is used to explicitly reference a symbol that is not referenced by any object file processed by the linker.  If any symbol appearing in a "REFERENCE" directive is not resolved by the linker, an error message will be issued for that symbol specifying that the symbol is undefined. 
The "REFERENCE" directive can be used to force object files from libraries to be linked with the application.  Also note that a symbol appearing in a "REFERENCE" directive will not be eliminated by dead code elimination.  For more information on dead code elimination, see the section entitled The ELIMINATE Option. 
The format of the "REFERENCE" directive (short form "REF") is as follows. 
    
     REFERENCE symbol_name{, symbol_name} 

symbol_name is the symbol for which a reference is made. 
Consider the following example. 
    
   reference domino 
The symbol domino will be searched for.  The object module that defines this symbol will be linked with the application.  Note that the linker will also attempt to resolve symbols referenced by this module.


#### QNX:  The SEGMENT Directive

The "SEGMENT" directive is used to describe the attributes of code and data segments.  The format of the "SEGMENT" directive (short form "SE") is as follows. 
    
     SEGMENT seg_desc{,seg_desc} 
     seg_desc ::= seg_id {seg_attrs}+ 
     seg_id ::= 'seg_name' | CLASS 'class_name' | TYPE [CODE | DATA] 
     seg_attrs ::= EXECUTEONLY | EXECUTEREAD 
               | READONLY | READWRITE 

seg_name is the name of the code or data segment whose attributes are being specified. 

class_name is a class name.  The attributes will be assigned to all segments belonging to the specified class. 

EXECUTEONLY (short form "EXECUTEO") specifies that the segment can only be executed.  This attribute should only be specified for code segments.  This attribute should not be specified if it is possible for the code segment to contain jump tables which is the case with the WATCOM C and FORTRAN optimizing compilers. 

EXECUTEREAD (short form "EXECUTER") specifies that the segment can only be executed and read.  This is the default for code segments.  This attribute should only be specified for code segments. 

READONLY (short form "READO") specifies that the segment can only be read.  This attribute should only be specified for data segments. 

READWRITE (short form "READW") specifies that the segment can be read and written.  This is the default for data segments.  This attribute should only be specified for data segments.


#### QNX:  The SORT Directive

The "SORT" directive is used to sort the symbols in the "Memory Map" section of the map file.  By default, symbols are listed on a per module basis in the order the modules were encountered by the linker.  That is, a module header is displayed followed by the symbols defined by the module. 
The format of the "SORT" directive (short form "SO") is as follows. 
    
     SORT [GLOBAL] [ALPHABETICAL] 
If the "SORT" directive is specified without any options, as in the following example, the module headers will be displayed each followed by the list of symbols it defines sorted by address. 
    
   sort 
If only the "GLOBAL" sort option (short form "GL") is specified, as in the following example, the module headers will not be displayed and all symbols will be sorted by address. 
    
   sort global 
If only the "ALPHABETICAL" sort option (short form "ALP") is specified, as in the following example, the module headers will be displayed each followed by the list of symbols it defines sorted alphabetically. 
    
   sort alphabetical 
If both the "GLOBAL" and "ALPHABETICAL" sort options are specified, as in the following example, the module headers will not be displayed and all symbols will be sorted alphabetically. 
    
   sort global alphabetical 
If you are linking a WATCOM C++ application, mangled names are sorted by using the base name.  The base name is the name of the symbol as it appeared in the source file.  See the section entitled The MANGLEDNAMES Option for more information on mangled names.


### QNX:  Memory Layout

The following describes the segment ordering of an application linked by the WATCOM Linker.  Note that this assumes that the "DOSSEG" linker option has been specified. 

 1.all segments not belonging to group "DGROUP" with class "CODE" 

 2.all other segments not belonging to group "DGROUP" 

 3.all segments belonging to group "DGROUP" with class "BEGDATA" 

 4.all segments belonging to group "DGROUP" not with class "BEGDATA", "BSS" or "STACK" 

 5.all segments belonging to group "DGROUP" with class "BSS" 

 6.all segments belonging to group "DGROUP" with class "STACK" 
A special segment belonging to class "BEGDATA" is defined when linking with WATCOM run-time libraries.  This segment is initialized with the hexadecimal byte pattern "01" and is the first segment in group "DGROUP" so that storing data at location 0 can be detected. 
Segments belonging to class "BSS" contain uninitialized data.  Note that this only includes uninitialized data in segments belonging to group "DGROUP".  Segments belonging to class "STACK" are used to define the size of the stack used for your application.  Segments belonging to the classes "BSS" and "STACK" are last in the segment ordering so that uninitialized data need not take space in the executable file.


### QNX:  The WATCOM Linker Memory Requirements

The WATCOM Linker uses all available memory when linking an application.  For DOS-hosted versions of the WATCOM Linker, this includes expanded memory (EMS) and extended memory.  It is possible for the size of the image being linked to exceed the amount of memory available in your machine, particularly if the image file is to contain debugging information. For this reason, a temporary disk file is used when all available memory is used by the WATCOM Linker. 
Normally, the temporary file is created in the current working directory.  However, by defining the "TMPDIR" environment variable to be a directory, you can tell the WATCOM Linker where to create the temporary file.  This can be particularly useful if you have a RAM disk.  Consider the following definition of the "TMPDIR" environment variable. 
    
   export TMPDIR=/tmp 
The WATCOM Linker will create the temporary file in the directory "/tmp".


## Windows:  The Windows Executable and DLL File Formats

This chapter deals with those aspects of the WATCOM Linker required to generate Windows executable files.  The Windows 3.x executable file format will only run under Windows 3.x.


### Windows:  The WATCOM Linker Command Line

Input to the WATCOM Linker is specified on the command line.  The following notation is used to describe the syntax of WATCOM Linker commands. 

ABC All items in upper case are required. 

[abc] The item abc is optional. 

{abc} The item abc may be repeated zero or more times. 

{abc}+ The item abc may be repeated one or more times. 

a|b|c One of a, b or c may be specified. 

a ::= b The item a is defined in terms of b. 
The WATCOM Linker command line format is as follows. 
    
   WLINK {directive} 
where directive is any of the following: 

ALIAS alias_name=symbol_name{,alias_name=symbol_name} 

| DEBUG [[WATCOM] db_list | CODEVIEW | DWARF] 
   db_list ::= [db_option{,db_option}] 
   db_option ::= LINES | TYPES | LOCALS | STATIC | ALL 

| DISABLE msg_num{,msg_num} 

| EXPORT export{,export} 

| EXPORT =lbc_file 
   export ::= entry_name[.n][=internal_name] [RESIDENT] 

| FILE obj_spec{,obj_spec} 
   obj_spec ::= obj_file[(obj_module)] | library_file[(obj_module)] 

| FORMAT WINDOWS [dll_form] [MEMORY] [FONT] 
   dll_form ::= DLL [INITGLOBAL | INITINSTANCE] 

| IMPORT import{,import} 
   import ::= internal_name module_name[.entry_name | n] 

| LIBFILE obj_file{,obj_file} 

| LIBPATH path_name{;path_name} 

| LIBRARY library_file{,library_file} 

| MODTRACE obj_module{,obj_module} 

| NAME exe_file 

| NEWSEGMENT 

| PATH path_name{;path_name} 

| OPTION option{,option} 
   option ::= ALIGNMENT=n | ARTIFICIAL 
           | [NO]CACHE | [NO]CASEEXACT 
           | DESCRIPTION 'string' 
           | DOSSEG | ELIMINATE | HEAPSIZE=n 
           | MANGLEDNAMES | MANYAUTODATA 
           | MAP[=map_file] | MAXERRORS=n 
           | MODNAME=module_name | NAMELEN=n 
           | NOAUTODATA | NODEFAULTLIBS 
           | OLDLIBRARY=dll_name | ONEAUTODATA 
           | OSNAME='string' | PACKCODE=n | PACKDATA=n 
           | QUIET | REDEFSOK 
           | RWRELOCCHECK 
           | STACK=n | STATIC | STUB=stub_name 
           | SYMFILE[=symbol_file] | UNDEFSOK 
           | VERBOSE | VERSION=major[.minor] 

| SEGMENT seg_desc{,seg_desc} 
   seg_desc ::= seg_id {seg_attrs}+ 
   seg_id ::= 'seg_name' | CLASS 'class_name' | TYPE [CODE | DATA] 
   seg_attrs ::= PRELOAD | LOADONCALL 
             | EXECUTEONLY | EXECUTEREAD 
             | READONLY | READWRITE 
             | SHARED | NONSHARED 
             | MOVEABLE | FIXED 
             | DISCARDABLE 

| SORT [GLOBAL] [ALPHABETICAL] 

| SYMTRACE symbol_name{,symbol_name} 

| SYSTEM BEGIN system_name {directive} END 

| SYSTEM system_name 

| # comment 

| @ directive_file 

class_name is a class name. 

comment is any sequence of characters. 

string is a sequence of characters. 

directive_file is a file specification for the name of a linker directive file.  If no file extension is specified, a file extension of "lnk" is assumed. 

dll_name is a file specification for the name of a dynamic link library.  If no file extension is specified, a file extension of "dll" is assumed. 

entry_name is a function name. 

exe_file is a file specification for the name of the executable file.  If no file extension is specified, a file extension of "exe" is assumed. 

internal_name is a function name. 

library_file is a file specification for the name of a library file.  If library_file appears in a "LIBRARY" directive and no file extension is specified, a file extension of "lib" is assumed.  If library_file appears in a "FILE" directive and no file extension is specified, a file extension of "obj" is assumed if you are running a DOS, OS/2 or Windows NT-hosted version of the WATCOM Linker.  A file extension of "o" is assumed if you are running a QNX-hosted version of the WATCOM Linker. 
When a library file is specified in a "FILE" directive and obj_module is specified, the object module identified by obj_module is extracted from the library file and included in the executable file.  If obj_module is not specified (only the library file is specified), all object modules in the library are included in the executable file. 

major specifies the major version number. 

lbc_file is a file specification for the name of a librarian command file.  If no file extension is specified, a file extension of "lbc" is assumed. 

map_file is a file specification for the name of the map file.  If no file extension is specified, a file extension of "map" is assumed. 

minor specifies the minor version number and must be less than 100. 

module_name is the name of a dynamic link library.  Note that this need not be the same as the file name of the executable file that contains the dynamic link library. 

n represents a value.  The complete form of n is the following. 
    
   [0x ] d { d } [ k | m ]
drepresentsadecimaldigit . If0xisspecified ,thestringofdigitsrepresentsahexadecimalnumber . Ifkisspecified ,thevalueismultipliedby1024 . Ifmisspecified ,thevalueismultipliedby1024 * 1024 .

obj_file is a file specification for the name of an object file.  If no file extension is specified, a file extension of "obj" is assumed if you are running a DOS, OS/2 or Windows NT-hosted version of the WATCOM Linker.  Also, if you are running a DOS, OS/2 or Windows NT-hosted version of the WATCOM Linker, the object file specification can contain wild cards (*, ?).  A file extension of "o" is assumed if you are running a QNX-hosted version of the WATCOM Linker. 

obj_module is the name of an object module contained in a library file or object file. 
Object files may contain multiple object modules.  A simple way of creating such an object file is to concatenate a number of object files into a single object file.  Each of the original object files is now an object module in the resulting object file.  Also, some language processors may generate object files that contain multiple object modules.  Specifying obj_module allows you to select a particular object module from an object file. 

path_name is a path name. 

msg_num is a message number. 

seg_name is the name of the code or data segment whose attributes are being specified. 

stub_name is a file specification for the name of the executable file.  If no file extension is specified, a file extension of "exe" is assumed. 

symbol_file is a file specification for the name of the symbol file.  If no file extension is specified, a file extension of "sym" is assumed. 

symbol_name is the name of a symbol. 

alias_name is the name of an alias symbol. 

system_name is the name of a system. 
You can view all the directives specific to Windows executable files by simply typing the following: 
    
   wlink ? win 
Notes: 

 1.If the file "wlink.hlp" is located in one of the paths specified in the "PATH" environment variable, the contents of that file will be displayed when the following command is issued. 
    
   wlink ? 

 2.If all of the directive information does not fit on the command line, type the following. 
    
   wlink 
The prompt "WLINK>" will appear on the next line.  You can enter as many lines of directive information as required.  Press "Ctrl/Z" followed by the "Enter" key to terminate the input of directive information if you are running a DOS, OS/2 or Windows NT-hosted version of the WATCOM Linker.  Press "Ctrl/D" to terminate the input of directive information if you are running a QNX-hosted version of the WATCOM Linker.


### Windows:  Fixed and Moveable Segments

All segments have attributes that tell Windows how to manage the segment.  One of these attributes specifies whether the segment is fixed or moveable.  Moveable segments can be moved in memory to satisfy other memory requests.  When a segment is moved, all near pointers to that segment are still valid since a near pointer references memory relative to the start of the segment.  However, far pointers are no longer valid once a segment has been moved.  Fixed segments, on the other hand, cannot be moved in memory.  A segment must be fixed if there exists far pointers to that segment that Windows cannot adjust if that segment were moved. 
Most segments, including code and data segments, are moveable.  Some exceptions exist.  If your program contains a far pointer, the segment which it references must be fixed.  If it were moveable, the segment address portion of the far pointer would be invalid when Windows moved the segment. 
All non-Windows programs are assigned fixed segments when they run under Windows.  These segments must be fixed since there is no information in the executable file that describes how segments are referenced.  Whenever possible, your application should consist of moveable segments since fixed segments can cause memory management problems.


### Windows:  Discardable Segments

Moveable segments can also be discardable.  Memory allocated to a discardable segment can be freed and used for other memory requests.  A "least recently used" (LRU) algorithm is used to determine which segment to discard when more memory is required. 
Discardable segments are usually segments that do not change once they are loaded into memory.  For example, code segments are discardable since programs do not usually modify their code segments.  When a segment is discarded, it can be reloaded into memory by accessing the executable file. 
Discardable segments must be moveable since they can be reloaded into a different area in memory than the area they previously occupied.  Note that moveable segments need not be discardable.  Obviously, data segments that contain read/write data cannot be discarded.


### Windows:  Dynamic Link Libraries

The WATCOM Linker can generate two forms of executable files; program modules and dynamic link libraries.  A program module is the executable file that gets loaded by Windows when you run your application.  A dynamic link library is really a library of routines that are called by a program module but not linked into the program module.  The executable code in a dynamic link library gets loaded by Windows during the execution of a program module when a routine in the dynamic link library is called. 
Program modules are contained in files whose name has a file extension of "exe".  Dynamic link libraries are contained in files whose name has a file extension of "dll".  The WATCOM Linker "FORMAT" directive can be used to select the type of executable file to be generated. 
Let us consider some of the advantages of using dynamic link libraries over standard libraries. 

 1.Functions in dynamic link libraries are not linked into your program.  Only references to the functions in dynamic link libraries are placed in the program module.  These references are called import definitions.  As a result, the linking time is reduced and disk space is saved.  If many applications reference the same dynamic link library, the saving in disk space can be significant. 

 2.Since program modules only reference dynamic link libraries and do not contain the actual executable code, a dynamic link library can be updated without re-linking your application.  When your application is executed, it will use the updated version of the dynamic link library. 

 3.Dynamic link libraries also allow sharing of code and data between the applications that use them.  If many applications that use the same dynamic link library are executing concurrently, the sharing of code and data segments improves memory utilization.


#### Windows:  Creating a Dynamic Link Library

To create a dynamic link library, you must specify the following form of the "FORMAT" directive. 
    
   format win dll 
In addition, you must specify which functions in the dynamic link library are to be made available to applications which use it.  This is achieved by using the "EXPORT" directive for each function that can be called by an application. 
Dynamic link libraries can reference other dynamic link libraries.  References to other dynamic link libraries are resolved by specifying "IMPORT" directives or using import libraries.


#### Windows:  Using a Dynamic Link Library

To use a dynamic link library, you must tell the WATCOM Linker which functions are contained in a dynamic link library and the name of the dynamic link library.  This is achieved in two ways. 
The first method is to use the "IMPORT" directive.  The "IMPORT" directive names the function and the dynamic link library it belongs to so that the WATCOM Linker can generate an import definition in the program module. 
The second method is to use import libraries.  An import library is a standard library which contains object modules with special object records that define the functions belonging to a dynamic link library.  An import library is created from a dynamic link library using the WATCOM Library Manager.  The resulting import library can then be specified in a "LIBRARY" directive in the same way one would specify a standard library.  See the chapter entitled "The WATCOM Library Manager" in the WATCOM Tools User's Guide for more information on creating import libraries. 
Using an import library is the preferred method of providing references to functions in dynamic link libraries.  When a dynamic link library is modified, typically the import library corresponding to the modified dynamic link library is updated to reflect the changes.  Hence, any directive file that specifies the import library in a "LIBRARY" directive need not be modified.  However, if you are using "IMPORT" directives, you may have to modify the "IMPORT" directives to reflect the changes in the dynamic link library.


### Windows:  WATCOM Linker Directives

Directives tell the WATCOM Linker how to create your program.  For example, using directives you can tell the WATCOM Linker which object files are to be included in the program, which library files to search to resolve undefined references, and the name of the executable file. 
The file WLINK.LNK is a special linker directive file that is automatically processed by the WATCOM Linker before processing any other directives.  On a DOS, OS/2 or Windows NT-hosted system, this file should be located in one of the paths specified in the PATH environment variable.  On a QNX-hosted system, this file should be located in the /etc directory.  A default version of this file is located in the \WATCOM\BIN directory on DOS-hosted systems, the \WATCOM\BINP directory on OS/2-hosted systems, the /etc directory on QNX-hosted systems, and the \WATCOM\BINNT directory on Windows NT-hosted systems.  Note that the file WLINK.LNK includes the file WLSYSTEM.LNK which is located in the \WATCOM\BINB directory on DOS, OS/2 and Windows NT-hosted systems and the /etc directory on QNX-hosted systems. 
The files WLINK.LNK and WLSYSTEM.LNK reference the WATCOM environment variable which must be set to the directory in which you installed your software. 
It is also possible to use environment variables when specifying a directive.  For example, if the LIBDIR environment variable is defined as follows, 
    
   set libdir=\test 
then the linker directive 
    
   library %libdir%\mylib 
is equivalent to the following linker directive. 
    
   library \test\mylib 
Note that a space must precede a reference to an environment variable. 
The following sections describe those WATCOM Linker directives that are used to generate Windows executable files.


#### Windows:  The ALIAS Directive

The "ALIAS" directive is used to specify an equivalent name for a symbol name.  The format of the "ALIAS" directive (short form "A") is as follows. 
    
     ALIAS alias_name=symbol_name{, alias_name=symbol_name} 

alias_name is the alias name. 

symbol_name is the symbol name to which the alias name is mapped. 
Consider the following example. 
    
   alias sine=mysine 
When the linker tries to resolve the reference to sine, it will immediately substitute the name mysine for sine and begin searching for the symbol mysine.


#### Windows:  The EXPORT Directive

The "EXPORT" directive can be used to define the names and attributes of functions in dynamic link libraries that are to be exported.  An "EXPORT" definition must be specified for every dynamic link library function that is to be made available externally.  An "EXPORT" directive is also required for the "window function".  This function must be defined by all programs and is called by Windows to provide information to the program.  For example, the window function is called when a window is created, destroyed or resized, when an item is selected from a menu, or when a scroll bar is being clicked with a mouse. 
The format of the "EXPORT" directive (short form "EXP") is as follows. 
    
     EXPORT export{,export} 
       or 
     EXPORT =lbc_file 
     export ::= entry_name[.ordinal][=internal_name] [RESIDENT] 

entry_name is the name to be used by other applications to call the function. 

ordinal is the ordinal value of the function.  If the ordinal number is specified, other applications can reference the function by using this ordinal number. 

internal_name is the actual name of the function and should only be specified if it differs from the entry name. 

RESIDENT specifies that the function's entry name should be kept resident in memory.  This applies only if the ordinal is specified.  If no ordinal is specified, the entry name is always memory resident.  Memory resident entry names allow Windows to resolve calls more efficiently when the call is by entry name rather than by ordinal. 

lbc_file is a file specification for the name of a librarian command file.  If no file extension is specified, a file extension of "lbc" is assumed.  The linker will process the librarian command file and look for commands to the librarian that are used to create import library entries.  These commands have the following form. 
    
   ++sym.dll_name[.export_name][.ordinal] 

sym is the name of a symbol in a dynamic link library. 

dll_name is the name of the dynamic link library that defines sym. 

ordinal is the ordinal value that can be used to identify sym instead of using the name export_name.  The default export name is sym. 

export_name is the name that an application that is linking to the dynamic link library uses to reference sym. 
All other librarian commands will be ignored. 
 Note:  By default, the WATCOM C compiler appends an underscore ('_') to all function names.  This should be considered when specifying entry_name and internal_name in an "EXPORT" directive.


#### Windows:  The FORMAT Directive

The "FORMAT" directive is used to specify the format of the executable file that the WATCOM Linker is to generate.  The format of the "FORMAT" directive (short form "FORM") is as follows. 
    
     FORMAT form 
     form ::= DOS [COM] 
           | WINDOWS [win_dll] [MEMORY] [FONT] 
           | WINDOWS NT [TNT] [dll_attrs] 
           | OS2 [os2_type] [dll_attrs | os2_attrs] 
           | PHARLAP [EXTENDED | REX] 
           | NOVELL [NLM | LAN | DSK | NAM] 'description' 
           | QNX [FLAT] 
           | ELF [DLL] 
     dll_attrs ::= DLL [INITGLOBAL | INITINSTANCE] 
              [TERMINSTANCE | TERMGLOBAL] 
     win_attrs ::= [win_dll] [MEMORY] [FONT] 
     win_dll ::= DLL [INITGLOBAL | INITINSTANCE] 
     os2_type ::= FLAT | LE | LX 
     os2_attrs ::= PM | PMCOMPATIBLE | FULLSCREEN 
               | PHYSDEVICE | VIRTDEVICE 

DOS (short form "D") tells the WATCOM Linker to generate a DOS "EXE" file.  For more information on DOS executable file formats, see the chapter entitled DOS:  The DOS Executable File Format. 

WINDOWS tells the WATCOM Linker to generate a Windows executable file.  The name of the executable file will have extension "exe".  If "DLL" (short form "DL") is specified, a dynamic link library will be generated; the name of the executable file will also have extension "exe".  Note that these default extensions can be overridden by using the "NAME" directive to name the executable file. 
Specifying "INITGLOBAL" (short form "INITG") will cause Windows to call an initialization routine the first time the dynamic link library is loaded.  Specifying "INITINSTANCE" (short form "INITI") will cause Windows to call an initialization routine each time the dynamic link library is used by a process.  In either case, the initialization routine is defined by the start address.  If neither "INITGLOBAL" or "INITINSTANCE" is specified, "INITGLOBAL" is assumed. 
Specifying "MEMORY" indicates that the application will run in standard or enhanced mode.  If Windows is running in standard and enhanced mode, and "MEMORY" is not specified, a warning message will be issued. 
Specifying "FONT" indicates that the proportional-spaced system font can be used.  Otherwise, the old-style mono-spaced system font will be used. 

WINDOWS NT tells the WATCOM Linker to generate a Windows NT executable file ("PE" format).  For more information on Windows NT executable file formats, see the chapter entitled NT:  The Windows NT Executable and DLL File Formats. 

OS2 tells the WATCOM Linker to generate an OS/2 executable file format.  For more information on OS/2 executable file formats, see the chapter entitled OS/2:  The OS/2 Executable and DLL File Formats. 

PHARLAP (short form "PHAR") tells the WATCOM Linker to generate an executable file that will run under Phar Lap's 386|DOS-Extender.  For more information on Phar Lap executable file formats, see the chapter entitled Phar Lap:  The Phar Lap Executable File Format. 

NOVELL (short form "NOV") tells the WATCOM Linker to generate a NetWare 386 executable file, more commonly called a NetWare Loadable Module (NLM).  For more information on NetWare 386 executable file formats, see the chapter entitled NetWare:  The NetWare 386 Executable File Format. 

QNX tells the WATCOM Linker to generate a QNX executable file.  For more information on QNX executable file formats, see the chapter entitled QNX:  The QNX Executable File Format. 

ELF tells the WATCOM Linker to generate an ELF format executable file. 
If no "FORMAT" directive is specified and you are running a DOS, OS/2 or Windows NT-hosted version of the WATCOM Linker, the executable file format will be selected in the following way. 

 1.If a reference to a dynamic link library is encountered, an OS/2 executable file will be generated. 

 2.If a 386 object module is encountered, an executable file that runs under Phar Lap's 386|DOS-Extender will be generated. 

 3.Otherwise, a DOS executable file will be generated. 
If no "FORMAT" directive is specified and you are running a QNX-hosted version of the WATCOM Linker, the executable file format will be selected in the following way. 

 1.If a reference to a dynamic link library is encountered, an OS/2 format executable file will be generated. 

 2.If a 386 object module is encountered, an executable file that runs under Phar Lap's 386|DOS-Extender will be generated. 

 3.Otherwise, a QNX executable file will be generated.


#### Windows:  The IMPORT Directive

The "IMPORT" directive describes a function that belongs to a dynamic link library.  The format of the "IMPORT" directive (short form "IMP") is as follows. 
    
     IMPORT import{,import} 
     import ::= internal_name module_name[.entry_name | ordinal] 

internal_name is the name the application used to call the function. 

module_name is the name of the dynamic link library.  Note that this need not be the same as the file name of the executable file containing the dynamic link library.  This name corresponds to the name specified by the "MODNAME" option when the dynamic link library was created. 

entry_name is the actual name of the function as defined in the dynamic link library. 

ordinal is the ordinal value of the function.  The ordinal number is an alternate method that can be used to reference a function in a dynamic link library. 
 Note:  By default, the WATCOM C compiler appends an underscore ('_') to all function names.  This should be considered when specifying internal_name and entry_name in an "IMPORT" directive. 
The preferred method to resolve references to dynamic link libraries is through the use of import libraries.  See the section entitled Windows:  Using a Dynamic Link Library for more information on import libraries.


#### Windows:  The OPTION Directive

The "OPTION" directive is used to specify options to the WATCOM Linker.  The format of the "OPTION" directive (short form "OP") is as follows. 
    
     OPTION option{,option} 
     option ::= ALIGNMENT=n | ARTIFICIAL 
             | [NO]CACHE | [NO]CASEEXACT 
             | DESCRIPTION 'string' 
             | DOSSEG | ELIMINATE | HEAPSIZE=n 
             | MANGLEDNAMES | MANYAUTODATA | MAP[=map_file] 
             | MAXERRORS=n | MODNAME=module_name | NAMELEN=n 
             | NOAUTODATA | NODEFAULTLIBS 
             | OLDLIBRARY=dll_name | ONEAUTODATA 
             | OSNAME='string' | PACKCODE=n | PACKDATA=n 
             | QUIET | REDEFSOK 
             | RWRELOCCHECK 
             | STACK=n | STATIC | STUB=stub_name 
             | SYMFILE[=symbol_file] | UNDEFSOK 
             | VERBOSE | VERSION=major[.minor] 

map_file is a file specification for the name of the map file.  If no file extension is specified, a file extension of "map" is assumed. 

symbol_file is a file specification for the name of the symbol file.  If no file extension is specified, a file extension of "sym" is assumed. 

module_name is the name of a program module or dynamic link library. 

dll_name is a file specification for the name of a dynamic link library.  If no file extension is specified, a file extension of "dll" is assumed. 

stub_name is a file specification for the name of the executable file.  If no file extension is specified, a file extension of "exe" is assumed. 

string is a sequence of characters. 

n represents a value.  The complete form of n is the following. 
    
   [0x]d{d}[k|m] 
d represents a decimal digit.  If 0x is specified, the string of digits represents a hexadecimal number.  If k is specified, the value is multiplied by 1024.  If m is specified, the value is multiplied by 1024*1024. 
The following sections describe the WATCOM Linker options specific to this executable format.  The options common to all executable formats are described in the chapter entitled General Directives and Options.


##### Windows:  The ALIGNMENT Option

The "ALIGNMENT" option specifies the alignment for segments in the executable file.  The format of the "ALIGNMENT" option (short form "A") is as follows. 
    
     OPTION ALIGNMENT=n 

n represents a value.  The complete form of n is the following. 
    
   [0x]d{d}[k|m] 
d represents a decimal digit.  If 0x is specified, the string of digits represents a hexadecimal number.  If k is specified, the value is multiplied by 1024.  If m is specified, the value is multiplied by 1024*1024. 
n specifies the alignment for segments in the executable file and must be a power of 2. 
Segments in the executable file are pointed to by a segment table.  An entry in the segment table contains a 16-bit value which is a multiple of the alignment value.  Together they form the offset of the segment from the start of the segment table.  Note that the smaller the value of n the smaller the executable file. 
By default, the WATCOM Linker will automatically choose the smallest value of n possible.  You need not specify this option unless you want padding between segments in the executable file.


##### Windows:  The DESCRIPTION Option

The "DESCRIPTION" option inserts the specified text into the application or dynamic link library.  This is useful if you wish to embed copyright information into an application or dynamic link library.  The format of the "DESCRIPTION" option (short form "DE") is as follows. 
    
     OPTION DESCRIPTION 'string' 

string is the sequence of characters to be embedded into the application or dynamic link library.


##### Windows:  The HEAPSIZE Option

The "HEAPSIZE" option specifies the size of the heap required by the application.  The format of the "HEAPSIZE" option (short form "H") is as follows. 
    
     OPTION HEAPSIZE=n 

n represents a value.  The complete form of n is the following. 
    
   [0x]d{d}[k|m] 
d represents a decimal digit.  If 0x is specified, the string of digits represents a hexadecimal number.  If k is specified, the value is multiplied by 1024.  If m is specified, the value is multiplied by 1024*1024. 
n specifies the size of the heap.  The default heap size is 0 bytes.  The maximum value of n is 65536 (64K) for 16-bit applications and 4G for 32-bit applications which is the maximum size of a physical segment.  Actually, for a particular application, the maximum value of n is 64K or 4G less the size of group "DGROUP".


##### Windows:  The MANYAUTODATA Option

The "MANYAUTODATA" option specifies that a copy of the automatic data segment (default data segment defined by the group "DGROUP"), for the program module or dynamic link library being created, is made for each instance.  The format of the "MANYAUTODATA" option (short form "MANY") is as follows. 
    
     OPTION MANYAUTODATA 
The default for a program module is "MANYAUTODATA" and for a dynamic link library is "ONEAUTODATA".


##### Windows:  The MODNAME Option

The "MODNAME" option specifies a name to be given to the module being created.  The format of the "MODNAME" option (short form "MODN") is as follows. 
    
     OPTION MODNAME=module_name 

module_name is the name of a dynamic link library. 
Once a module has been loaded (whether it be a program module or a dynamic link library), mod_name is the name of the module known to Windows.  If the "MODNAME" option is not used to specify a module name, the default module name is the name of the executable file without the file extension.


##### Windows:  The NOAUTODATA Option

The "NOAUTODATA" option specifies that no automatic data segment (default data segment defined by the group "DGROUP"), exists for the program module or dynamic link library being created.  The format of the "NOAUTODATA" option (short form "NOA") is as follows. 
    
     OPTION NOAUTODATA


##### Windows:  The OLDLIBRARY Option

The "OLDLIBRARY" option is used to preserve the export ordinals for successive versions of a dynamic link library.  This ensures that any application that references functions in a dynamic link library by ordinal will continue to execute correctly.  The format of the "OLDLIBRARY" option (short form "OLD") is as follows. 
    
     OPTION OLDLIBRARY=dll_name 

dll_name is a file specification for the name of a dynamic link library.  If no file extension is specified, a file extension of "dll" is assumed. 
Only the current directory or a specified directory will be searched for dynamic link libraries specified in the "OLDLIBRARY" option.


##### Windows:  The ONEAUTODATA Option

The "ONEAUTODATA" option specifies that the automatic data segment (default data segment defined by the group "DGROUP") for the program module or dynamic link library being created will be shared by all instances.  The format of the "ONEAUTODATA" option (short form "ONE") is as follows. 
    
     OPTION ONEAUTODATA 
The default for a dynamic link library is "ONEAUTODATA" and for a program module is "MANYAUTODATA".


##### Windows:  The PACKDATA Option

By default, the WATCOM Linker automatically groups logical code segments into physical segments.  The "PACKDATA" option is used to specify the size of the physical segment.  The format of the "PACKCODE" option (short form "PACKD") is as follows. 
    
     OPTION PACKDATA=n 

n represents a value.  The complete form of n is the following. 
    
   [0x]d{d}[k|m] 
d represents a decimal digit.  If 0x is specified, the string of digits represents a hexadecimal number.  If k is specified, the value is multiplied by 1024.  If m is specified, the value is multiplied by 1024*1024. 
n specifies the size of the physical segments into which far data segments are packed.  The default value of n is 64K.  Note that this is also the maximum size of a physical segment.  To suppress automatic grouping of far data segments, specify a value of 0 for n. 
Notes: 

 1.Only adjacent segments are packed into a physical segment. 

 2.Segments belonging to the same group are packed in a physical segment.  Segments belonging to different groups are not packed into a physical segment. 

 3.Segments with different attributes are not packed together unless they are explicitly grouped.


##### Windows:  The RWRELOCCHECK Option

The "RWRELOCCHECK" option causes the linker to check for segment relocations to a read/write data segment and issue a warning if any are found.  This option is useful if you are building a windows application that may have more than one instance running at a given time. 
The format of the "RWRELOCCHECK" option (short form "RWR") is as follows. 
    
     OPTION RWRELOCCHECK


##### Windows:  The STUB Option

The "STUB" option specifies an executable file that is to be placed at the beginning of the Windows executable file being generated.  This program will be executed if the Windows module is executed under DOS.  The format of the "STUB" option is as follows. 
    
     OPTION STUB=stub_name 

stub_name is a file specification for the name of the stub executable file.  If no file extension is specified, a file extension of "exe" is assumed. 
The WATCOM Linker will search all paths specified in the "path" environment variable for the stub executable file.  The stub executable file specified by the "STUB" option must not be the same as the executable file being generated.


##### Windows:  The VERSION Option

The "VERSION" option can be used to identify the application so that it can be distinguished from other versions (releases) of the same application.  This option is most useful when creating a DLL since applications that use the DLL may only execute with a specific version of the DLL. 
The format of the "VERSION" option (short form "VER") is as follows. 
    
     OPTION VERSION=major[.minor] 

major specifies the major version number. 

minor specifies the minor version number and must be less than 100.


#### Windows:  The REFERENCE Directive

The "REFERENCE" directive is used to explicitly reference a symbol that is not referenced by any object file processed by the linker.  If any symbol appearing in a "REFERENCE" directive is not resolved by the linker, an error message will be issued for that symbol specifying that the symbol is undefined. 
The "REFERENCE" directive can be used to force object files from libraries to be linked with the application.  Also note that a symbol appearing in a "REFERENCE" directive will not be eliminated by dead code elimination.  For more information on dead code elimination, see the section entitled The ELIMINATE Option. 
The format of the "REFERENCE" directive (short form "REF") is as follows. 
    
     REFERENCE symbol_name{, symbol_name} 

symbol_name is the symbol for which a reference is made. 
Consider the following example. 
    
   reference domino 
The symbol domino will be searched for.  The object module that defines this symbol will be linked with the application.  Note that the linker will also attempt to resolve symbols referenced by this module.


#### Windows:  The SEGMENT Directive

The "SEGMENT" directive is used to describe the attributes of code and data segments.  The format of the "SEGMENT" directive (short form "SE") is as follows. 
    
     SEGMENT seg_desc{,seg_desc} 
     seg_desc ::= seg_id {seg_attrs}+ 
     seg_id ::= 'seg_name' | CLASS 'class_name' | TYPE [CODE | DATA] 
     seg_attrs ::= PRELOAD | LOADONCALL 
               | EXECUTEONLY | EXECUTEREAD 
               | READONLY | READWRITE 
               | SHARED | NONSHARED 
               | MOVEABLE | FIXED 
               | DISCARDABLE 

seg_name is the name of the code or data segment whose attributes are being specified. 

class_name is a class name.  The attributes will be assigned to all segments belonging to the specified class. 

PRELOAD (short form "PR") specifies that the segment is loaded as soon as the executable file is loaded.  This is the default. 

LOADONCALL (short form "LO") specifies that the segment is loaded only when accessed. 

EXECUTEONLY (short form "EXECUTEO") specifies that the segment can only be executed.  This attribute should only be specified for code segments.  This attribute should not be specified if it is possible for the code segment to contain jump tables which is the case with the WATCOM C and FORTRAN optimizing compilers. 

EXECUTEREAD (short form "EXECUTER") specifies that the segment can only be executed and read.  This attribute, the default for code segments, should only be specified for code segments.  This attribute is appropriate for code segments that contain jump tables as is possible with the WATCOM C and FORTRAN optimizing compilers. 

READONLY (short form "READO") specifies that the segment can only be read.  This attribute should only be specified for data segments. 

READWRITE (short form "READW") specifies that the segment can be read and written.  This is the default for data segments.  This attribute should only be specified for data segments. 

SHARED (short form "SH" ) specifies that a single copy of the segment will be loaded and will be shared by all processes. 

NONSHARED (short form "NONS") specifies that a unique copy of the segment will be loaded for each process.  This is the default. 

MOVEABLE (short form "MOV") specifies that the segment is moveable.  By default, segments are moveable. 

FIXED (short form "FIX") specifies that the segment is fixed. 

DISCARDABLE (short form "DIS") specifies that the segment is discardable.  By default, segments are not discardable. 
 Note:  Attributes specified for segments identified by a segment name override attributes specified for segments identified by a class name.


#### Windows:  The SORT Directive

The "SORT" directive is used to sort the symbols in the "Memory Map" section of the map file.  By default, symbols are listed on a per module basis in the order the modules were encountered by the linker.  That is, a module header is displayed followed by the symbols defined by the module. 
The format of the "SORT" directive (short form "SO") is as follows. 
    
     SORT [GLOBAL] [ALPHABETICAL] 
If the "SORT" directive is specified without any options, as in the following example, the module headers will be displayed each followed by the list of symbols it defines sorted by address. 
    
   sort 
If only the "GLOBAL" sort option (short form "GL") is specified, as in the following example, the module headers will not be displayed and all symbols will be sorted by address. 
    
   sort global 
If only the "ALPHABETICAL" sort option (short form "ALP") is specified, as in the following example, the module headers will be displayed each followed by the list of symbols it defines sorted alphabetically. 
    
   sort alphabetical 
If both the "GLOBAL" and "ALPHABETICAL" sort options are specified, as in the following example, the module headers will not be displayed and all symbols will be sorted alphabetically. 
    
   sort global alphabetical 
If you are linking a WATCOM C++ application, mangled names are sorted by using the base name.  The base name is the name of the symbol as it appeared in the source file.  See the section entitled The MANGLEDNAMES Option for more information on mangled names.


### Windows:  Memory Layout

The following describes the segment ordering of an application linked by the WATCOM Linker.  Note that this assumes that the "DOSSEG" linker option has been specified. 

 1.all segments not belonging to group "DGROUP" with class "CODE" 

 2.all other segments not belonging to group "DGROUP" 

 3.all segments belonging to group "DGROUP" with class "BEGDATA" 

 4.all segments belonging to group "DGROUP" not with class "BEGDATA", "BSS" or "STACK" 

 5.all segments belonging to group "DGROUP" with class "BSS" 

 6.all segments belonging to group "DGROUP" with class "STACK" 
A special segment belonging to class "BEGDATA" is defined when linking with WATCOM run-time libraries.  This segment is initialized with the hexadecimal byte pattern "01" and is the first segment in group "DGROUP" so that storing data at location 0 can be detected. 
Segments belonging to class "BSS" contain uninitialized data.  Note that this only includes uninitialized data in segments belonging to group "DGROUP".  Segments belonging to class "STACK" are used to define the size of the stack used for your application.  Segments belonging to the classes "BSS" and "STACK" are last in the segment ordering so that uninitialized data need not take space in the executable file.


### Windows:  The WATCOM Linker Memory Requirements

The WATCOM Linker uses all available memory when linking an application.  For DOS-hosted versions of the WATCOM Linker, this includes expanded memory (EMS) and extended memory.  It is possible for the size of the image being linked to exceed the amount of memory available in your machine, particularly if the image file is to contain debugging information. For this reason, a temporary disk file is used when all available memory is used by the WATCOM Linker. 
Normally, the temporary file is created in the default directory.  However, by defining the "tmp" environment variable to be a directory, you can tell the WATCOM Linker where to create the temporary file.  This can be particularly useful if you have a RAM disk.  Consider the following definition of the "tmp" environment variable. 
    
   set tmp=\tmp 
The WATCOM Linker will create the temporary file in the directory "\tmp".


### Windows:  Converting Microsoft Response Files to Directive Files

A utility called MS2WLINK can be used to convert Microsoft linker response files to WATCOM Linker directive files.  Input to MS2WLINK is processed in the same way as the Microsoft linker processes its input, the difference being MS2WLINK lists the corresponding WATCOM Linker directive file to the standard output device instead of a creating an executable file.  The resulting output can be redirected to a disk file which can then be used as input to the WATCOM Linker to produce an executable file. 
Suppose you have a Microsoft linker response file called "test.rsp".  You can convert this file to a WATCOM Linker directive file by issuing the following command. 
Example: 
   ms2wlink @test.rsp >test.lnk 
You can now use the WATCOM Linker to link your program by issuing the following command. 
Example: 
   wlink @test 
An alternative way to link your application with the WATCOM Linker from a Microsoft response file is to issue the following command. 
Example: 
   ms2wlink @test.rsp | wlink 
Since the WATCOM Linker gets its input from the standard input device, you do not have to create a WATCOM Linker directive file to link your application. 
Note that MS2WLINK can also process module-definition files used for creating OS/2 applications.


## NT:  The Windows NT Executable and DLL File Formats

This chapter deals with those aspects of the WATCOM Linker required to generate Windows NT executable files.  The Windows NT executable file format will only run under Windows NT and Phar Lap's TNT DOS extender.


### NT:  The WATCOM Linker Command Line

Input to the WATCOM Linker is specified on the command line.  The following notation is used to describe the syntax of WATCOM Linker commands. 

ABC All items in upper case are required. 

[abc] The item abc is optional. 

{abc} The item abc may be repeated zero or more times. 

{abc}+ The item abc may be repeated one or more times. 

a|b|c One of a, b or c may be specified. 

a ::= b The item a is defined in terms of b. 
The WATCOM Linker command line format is as follows. 
    
   WLINK {directive} 
where directive is any of the following: 

ALIAS alias_name=symbol_name{,alias_name=symbol_name} 

| COMMIT mem_type 
   mem_type ::= STACK=n | HEAP=n 

| DEBUG [[WATCOM] db_list | CODEVIEW | DWARF] 
   db_list ::= [db_option{,db_option}] 
   db_option ::= LINES | TYPES | LOCALS | STATIC | ALL 

| DISABLE msg_num{,msg_num} 

| EXPORT export{,export} 

| EXPORT =lbc_file 
   export ::= entry_name[.n][=internal_name] [RESIDENT] 

| FILE obj_spec{,obj_spec} 
   obj_spec ::= obj_file[(obj_module)] | library_file[(obj_module)] 

| FORMAT WINDOWS NT [TNT] [dll_form] 
   dll_form ::= DLL [INITGLOBAL | INITINSTANCE] 
            [TERMGLOBAL | TERMINSTANCE] 

| IMPORT import{,import} 
   import ::= internal_name module_name[.entry_name | n] 

| LIBFILE obj_file{,obj_file} 

| LIBPATH path_name{;path_name} 

| LIBRARY library_file{,library_file} 

| MODTRACE obj_module{,obj_module} 

| NAME exe_file 

| PATH path_name{;path_name} 

| OPTION option{,option} 
   option ::= ALIGNMENT=n | ARTIFICIAL 
           | [NO]CACHE | [NO]CASEEXACT 
           | DESCRIPTION 'string' 
           | DOSSEG | ELIMINATE | HEAPSIZE=n 
           | MANGLEDNAMES | MANYAUTODATA 
           | MAP[=map_file] | MAXERRORS=n 
           | MODNAME=module_name | NAMELEN=n 
           | NOAUTODATA | NODEFAULTLIBS 
           | OBJALIGN=n 
           | OLDLIBRARY=dll_name | ONEAUTODATA 
           | OSNAME='string' | PACKCODE=n | PACKDATA=n 
           | QUIET | REDEFSOK 
           | STACK=n | STATIC | STUB=stub_name 
           | SYMFILE[=symbol_file] | UNDEFSOK 
           | VERBOSE | VERSION=major[.minor] 

| SEGMENT seg_desc{,seg_desc} 
   seg_desc ::= seg_id {seg_attrs}+ 
   seg_id ::= 'seg_name' | CLASS 'class_name' | TYPE [CODE | DATA] 
   seg_attrs ::= PAGEABLE | NONPAGEABLE 
             | SHARED | NONSHARED 

| SORT [GLOBAL] [ALPHABETICAL] 

| SYMTRACE symbol_name{,symbol_name} 

| SYSTEM BEGIN system_name {directive} END 

| SYSTEM system_name 

| # comment 

| @ directive_file 

class_name is a class name. 

comment is any sequence of characters. 

string is a sequence of characters. 

directive_file is a file specification for the name of a linker directive file.  If no file extension is specified, a file extension of "lnk" is assumed. 

dll_name is a file specification for the name of a dynamic link library.  If no file extension is specified, a file extension of "dll" is assumed. 

entry_name is a function name. 

exe_file is a file specification for the name of the executable file.  If no file extension is specified, a file extension of "exe" is assumed. 

internal_name is a function name. 

library_file is a file specification for the name of a library file.  If library_file appears in a "LIBRARY" directive and no file extension is specified, a file extension of "lib" is assumed.  If library_file appears in a "FILE" directive and no file extension is specified, a file extension of "obj" is assumed if you are running a DOS, OS/2 or Windows NT-hosted version of the WATCOM Linker.  A file extension of "o" is assumed if you are running a QNX-hosted version of the WATCOM Linker. 
When a library file is specified in a "FILE" directive and obj_module is specified, the object module identified by obj_module is extracted from the library file and included in the executable file.  If obj_module is not specified (only the library file is specified), all object modules in the library are included in the executable file. 

major specifies the major version number. 

lbc_file is a file specification for the name of a librarian command file.  If no file extension is specified, a file extension of "lbc" is assumed. 

map_file is a file specification for the name of the map file.  If no file extension is specified, a file extension of "map" is assumed. 

minor specifies the minor version number and must be less than 100. 

module_name is the name of a dynamic link library.  Note that this need not be the same as the file name of the executable file that contains the dynamic link library. 

n represents a value.  The complete form of n is the following. 
    
   [0x]d{d}[k|m ]
drepresentsadecimaldigit . If0xisspecified ,thestringofdigitsrepresentsahexadecimalnumber . Ifkisspecified ,thevalueismultipliedby1024 . Ifmisspecified ,thevalueismultipliedby1024 * 1024 .

obj_file is a file specification for the name of an object file.  If no file extension is specified, a file extension of "obj" is assumed if you are running a DOS, OS/2 or Windows NT-hosted version of the WATCOM Linker.  Also, if you are running a DOS, OS/2 or Windows NT-hosted version of the WATCOM Linker, the object file specification can contain wild cards (*, ?).  A file extension of "o" is assumed if you are running a QNX-hosted version of the WATCOM Linker. 

obj_module is the name of an object module contained in a library file or object file. 
Object files may contain multiple object modules.  A simple way of creating such an object file is to concatenate a number of object files into a single object file.  Each of the original object files is now an object module in the resulting object file.  Also, some language processors may generate object files that contain multiple object modules.  Specifying obj_module allows you to select a particular object module from an object file. 

path_name is a path name. 

msg_num is a message number. 

seg_name is the name of the code or data segment whose attributes are being specified. 

stub_name is a file specification for the name of the executable file.  If no file extension is specified, a file extension of "exe" is assumed. 

symbol_file is a file specification for the name of the symbol file.  If no file extension is specified, a file extension of "sym" is assumed. 

symbol_name is the name of a symbol. 

alias_name is the name of an alias symbol. 

system_name is the name of a system. 
You can view all the directives specific to Windows NT executable files by simply typing the following: 
    
   wlink ? nt 
Notes: 

 1.If the file "wlink.hlp" is located in one of the paths specified in the "PATH" environment variable, the contents of that file will be displayed when the following command is issued. 
    
   wlink ? 

 2.If all of the directive information does not fit on the command line, type the following. 
    
   wlink 
The prompt "WLINK>" will appear on the next line.  You can enter as many lines of directive information as required.  Press "Ctrl/Z" followed by the "Enter" key to terminate the input of directive information if you are running a DOS, OS/2 or Windows NT-hosted version of the WATCOM Linker.  Press "Ctrl/D" to terminate the input of directive information if you are running a QNX-hosted version of the WATCOM Linker.


### NT:  Dynamic Link Libraries

The WATCOM Linker can generate two forms of executable files; program modules and dynamic link libraries.  A program module is the executable file that gets loaded by Windows NT when you run your application.  A dynamic link library is really a library of routines that are called by a program module but not linked into the program module.  The executable code in a dynamic link library gets loaded by Windows NT during the execution of a program module when a routine in the dynamic link library is called. 
Program modules are contained in files whose name has a file extension of "exe".  Dynamic link libraries are contained in files whose name has a file extension of "dll".  The WATCOM Linker "FORMAT" directive can be used to select the type of executable file to be generated. 
Let us consider some of the advantages of using dynamic link libraries over standard libraries. 

 1.Functions in dynamic link libraries are not linked into your program.  Only references to the functions in dynamic link libraries are placed in the program module.  These references are called import definitions.  As a result, the linking time is reduced and disk space is saved.  If many applications reference the same dynamic link library, the saving in disk space can be significant. 

 2.Since program modules only reference dynamic link libraries and do not contain the actual executable code, a dynamic link library can be updated without re-linking your application.  When your application is executed, it will use the updated version of the dynamic link library. 

 3.Dynamic link libraries also allow sharing of code and data between the applications that use them.  If many applications that use the same dynamic link library are executing concurrently, the sharing of code and data segments improves memory utilization.


#### NT:  Creating a Dynamic Link Library

To create a dynamic link library, you must specify the following form of the "FORMAT" directive. 
    
   format win nt dll 
In addition, you must specify which functions in the dynamic link library are to be made available to applications which use it.  This is achieved by using the "EXPORT" directive for each function that can be called by an application. 
Dynamic link libraries can reference other dynamic link libraries.  References to other dynamic link libraries are resolved by specifying "IMPORT" directives or using import libraries.


#### NT:  Using a Dynamic Link Library

To use a dynamic link library, you must tell the WATCOM Linker which functions are contained in a dynamic link library and the name of the dynamic link library.  This is achieved in two ways. 
The first method is to use the "IMPORT" directive.  The "IMPORT" directive names the function and the dynamic link library it belongs to so that the WATCOM Linker can generate an import definition in the program module. 
The second method is to use import libraries.  An import library is a standard library which contains object modules with special object records that define the functions belonging to a dynamic link library.  An import library is created from a dynamic link library using the WATCOM Library Manager.  The resulting import library can then be specified in a "LIBRARY" directive in the same way one would specify a standard library.  See the chapter entitled "The WATCOM Library Manager" in the WATCOM Tools User's Guide for more information on creating import libraries. 
Using an import library is the preferred method of providing references to functions in dynamic link libraries.  When a dynamic link library is modified, typically the import library corresponding to the modified dynamic link library is updated to reflect the changes.  Hence, any directive file that specifies the import library in a "LIBRARY" directive need not be modified.  However, if you are using "IMPORT" directives, you may have to modify the "IMPORT" directives to reflect the changes in the dynamic link library.


### NT:  WATCOM Linker Directives

Directives tell the WATCOM Linker how to create your program.  For example, using directives you can tell the WATCOM Linker which object files are to be included in the program, which library files to search to resolve undefined references, and the name of the executable file. 
The file WLINK.LNK is a special linker directive file that is automatically processed by the WATCOM Linker before processing any other directives.  On a DOS, OS/2 or Windows NT-hosted system, this file should be located in one of the paths specified in the PATH environment variable.  On a QNX-hosted system, this file should be located in the /etc directory.  A default version of this file is located in the \WATCOM\BIN directory on DOS-hosted systems, the \WATCOM\BINP directory on OS/2-hosted systems, the /etc directory on QNX-hosted systems, and the \WATCOM\BINNT directory on Windows NT-hosted systems.  Note that the file WLINK.LNK includes the file WLSYSTEM.LNK which is located in the \WATCOM\BINB directory on DOS, OS/2 and Windows NT-hosted systems and the /etc directory on QNX-hosted systems. 
The files WLINK.LNK and WLSYSTEM.LNK reference the WATCOM environment variable which must be set to the directory in which you installed your software. 
It is also possible to use environment variables when specifying a directive.  For example, if the LIBDIR environment variable is defined as follows, 
    
   set libdir=\test 
then the linker directive 
    
   library %libdir%\mylib 
is equivalent to the following linker directive. 
    
   library \test\mylib 
Note that a space must precede a reference to an environment variable. 
The following sections describe those WATCOM Linker directives that are used to generate Windows NT executable files.


#### NT:  The ALIAS Directive

The "ALIAS" directive is used to specify an equivalent name for a symbol name.  The format of the "ALIAS" directive (short form "A") is as follows. 
    
     ALIAS alias_name=symbol_name{, alias_name=symbol_name} 

alias_name is the alias name. 

symbol_name is the symbol name to which the alias name is mapped. 
Consider the following example. 
    
   alias sine=mysine 
When the linker tries to resolve the reference to sine, it will immediately substitute the name mysine for sine and begin searching for the symbol mysine.


#### NT:  The COMMIT Directive

When the Windows NT operating system allocates the stack and heap for an application, it does not actually allocate the whole stack and heap to the application when it is initially loaded.  Instead, only a portion of the stack and heap are allocated or committed to the application.  Any part of the stack and heap that is not committed will be committed on demand. 
By default, a 4k heap is committed to the application.  The size specified by the "STACK" option is used as the amount of stack to commit when the application is loaded.  See the section entitled The STACK Option for more information on specifying a stack size. 
The format of the "COMMIT" directive (short form "COM") is as follows. 
    
     COMMIT mem_type 
     mem_type ::= STACK=n | HEAP=n 

n represents a value.  The complete form of n is the following. 
    
   [0x]d{d}[k|m] 
d represents a decimal digit.  If 0x is specified, the string of digits represents a hexadecimal number.  If k is specified, the value is multiplied by 1024.  If m is specified, the value is multiplied by 1024*1024. 
n represents the amout of stack or heap that is initially committed to the application.


#### NT:  The EXPORT Directive

The "EXPORT" directive can be used to define the names and attributes of functions in dynamic link libraries that are to be exported.  An "EXPORT" definition must be specified for every dynamic link library function that is to be made available externally. 
The format of the "EXPORT" directive (short form "EXP") is as follows. 
    
     EXPORT export{,export} 
       or 
     EXPORT =lbc_file 

entry_name is the name to be used by other applications to call the function. 

ordinal is the ordinal value of the function.  If the ordinal number is specified, other applications can reference the function by using this ordinal number. 

internal_name is the actual name of the function and should only be specified if it differs from the entry name. 

RESIDENT specifies that the function's entry name should be kept resident in memory.  This applies only if the ordinal is specified.  If no ordinal is specified, the entry name is always memory resident.  Memory resident entry names allow Windows NT to resolve calls more efficiently when the call is by entry name rather than by ordinal. 

lbc_file is a file specification for the name of a librarian command file.  If no file extension is specified, a file extension of "lbc" is assumed.  The linker will process the librarian command file and look for commands to the librarian that are used to create import library entries.  These commands have the following form. 
    
   ++sym.dll_name[.export_name][.ordinal] 

sym is the name of a symbol in a dynamic link library. 

dll_name is the name of the dynamic link library that defines sym. 

ordinal is the ordinal value that can be used to identify sym instead of using the name export_name.  The default export name is sym. 

export_name is the name that an application that is linking to the dynamic link library uses to reference sym. 
All other librarian commands will be ignored. 
 Note:  By default, the WATCOM C compiler appends an underscore ('_') to all function names.  This should be considered when specifying entry_name and internal_name in an "EXPORT" directive.


#### NT:  The FORMAT Directive

The "FORMAT" directive is used to specify the format of the executable file that the WATCOM Linker is to generate.  The format of the "FORMAT" directive (short form "FORM") is as follows. 
    
     FORMAT form 
     form ::= DOS [COM] 
           | WINDOWS [win_dll] [MEMORY] [FONT] 
           | WINDOWS NT [TNT] [dll_attrs] 
           | OS2 [os2_type] [dll_attrs | os2_attrs] 
           | PHARLAP [EXTENDED | REX] 
           | NOVELL [NLM | LAN | DSK | NAM] 'description' 
           | QNX [FLAT] 
           | ELF [DLL] 
     dll_attrs ::= DLL [INITGLOBAL | INITINSTANCE] 
              [TERMINSTANCE | TERMGLOBAL] 
     win_attrs ::= [win_dll] [MEMORY] [FONT] 
     win_dll ::= DLL [INITGLOBAL | INITINSTANCE] 
     os2_type ::= FLAT | LE | LX 
     os2_attrs ::= PM | PMCOMPATIBLE | FULLSCREEN 
               | PHYSDEVICE | VIRTDEVICE 

DOS (short form "D") tells the WATCOM Linker to generate a DOS "EXE" file.  For more information on DOS executable file formats, see the chapter entitled DOS:  The DOS Executable File Format. 

WINDOWS tells the WATCOM Linker to generate a Windows executable file.  For more information on Windows executable file formats, see the chapter entitled Windows:  The Windows Executable and DLL File Formats. 

WINDOWS NT tells the WATCOM Linker to generate a Windows NT executable file ("PE" format). 
If "TNT" is specified, an executable for the Phar Lap TNT DOS extender is created.  A "PL" format (rather than "PE") executable is created so that the Phar Lap TNT DOS extender will always run the application (including under Windows NT). 
If "DLL" (short form "DL") is specified, a dynamic link library will be generated in which case the name of the executable file will have extension "dll".  Note that these default extensions can be overridden by using the "NAME" directive to name the executable file. 
Specifying INITGLOBAL (short form "INITG") will cause the initialization routine to be called the first time the dynamic link library is loaded.  Specifying INITINSTANCE (short form "INITI") will cause the initialization routine to be called each time the dynamic link library is referenced by a process.  If neither "INITGLOBAL" or "INITINSTANCE" is specified, "INITGLOBAL" is assumed.  It is also possible to specify whether the initialization routine is to be called at DLL termination or not.  Specifying TERMGLOBAL (short form "TERMG") will cause the initialization routine to be called when the last instance of the dynamic link library is terminated.  Specifying TERMINSTANCE (short form "TERMI") will cause the initialization routine to be called each time an instance of the dynamic link library is terminated.  Note that the initialization routine is passed an argument indicating whether it is being called during DLL initialization or DLL termination.  If "INITINSTANCE" is used and no termination option is specified, "TERMINSTANCE" is assumed.  If "INITGLOBAL" is used and no termination option is specified, "TERMGLOBAL" is assumed. 

OS2 tells the WATCOM Linker to generate an OS/2 executable file format.  For more information on OS/2 executable file formats, see the chapter entitled OS/2:  The OS/2 Executable and DLL File Formats. 

PHARLAP (short form "PHAR") tells the WATCOM Linker to generate an executable file that will run under Phar Lap's 386|DOS-Extender.  For more information on Phar Lap executable file formats, see the chapter entitled Phar Lap:  The Phar Lap Executable File Format. 

NOVELL (short form "NOV") tells the WATCOM Linker to generate a NetWare 386 executable file, more commonly called a NetWare Loadable Module (NLM).  For more information on NetWare 386 executable file formats, see the chapter entitled NetWare:  The NetWare 386 Executable File Format. 

QNX tells the WATCOM Linker to generate a QNX executable file.  For more information on QNX executable file formats, see the chapter entitled QNX:  The QNX Executable File Format. 

ELF tells the WATCOM Linker to generate an ELF format executable file. 
If no "FORMAT" directive is specified and you are running a DOS, OS/2 or Windows NT-hosted version of the WATCOM Linker, the executable file format will be selected in the following way. 

 1.If a reference to a dynamic link library is encountered, an OS/2 executable file will be generated. 

 2.If a 386 object module is encountered, an executable file that runs under Phar Lap's 386|DOS-Extender will be generated. 

 3.Otherwise, a DOS executable file will be generated. 
If no "FORMAT" directive is specified and you are running a QNX-hosted version of the WATCOM Linker, the executable file format will be selected in the following way. 

 1.If a reference to a dynamic link library is encountered, an OS/2 format executable file will be generated. 

 2.If a 386 object module is encountered, an executable file that runs under Phar Lap's 386|DOS-Extender will be generated. 

 3.Otherwise, a QNX executable file will be generated.


#### NT:  The IMPORT Directive

The "IMPORT" directive describes a function that belongs to a dynamic link library.  The format of the "IMPORT" directive (short form "IMP") is as follows. 
    
     IMPORT import{,import} 
     import ::= internal_name module_name[.entry_name | ordinal] 

internal_name is the name the application used to call the function. 

module_name is the name of the dynamic link library.  Note that this need not be the same as the file name of the executable file containing the dynamic link library.  This name corresponds to the name specified by the "MODNAME" option when the dynamic link library was created. 

entry_name is the actual name of the function as defined in the dynamic link library. 

ordinal is the ordinal value of the function.  The ordinal number is an alternate method that can be used to reference a function in a dynamic link library. 
 Note:  By default, the WATCOM C compiler appends an underscore ('_') to all function names.  This should be considered when specifying internal_name and entry_name in an "IMPORT" directive. 
The preferred method to resolve references to dynamic link libraries is through the use of import libraries.  See the section entitled NT:  Using a Dynamic Link Library for more information on import libraries.


#### NT:  The OPTION Directive

The "OPTION" directive is used to specify options to the WATCOM Linker.  The format of the "OPTION" directive (short form "OP") is as follows. 
    
     OPTION option{,option} 
     option ::= ALIGNMENT=n | ARTIFICIAL 
             | [NO]CACHE | [NO]CASEEXACT 
             | DESCRIPTION 'string' 
             | DOSSEG | ELIMINATE | HEAPSIZE=n 
             | MANGLEDNAMES | MANYAUTODATA | MAP[=map_file] 
             | MAXERRORS=n | MODNAME=module_name | NAMELEN=n 
             | NOAUTODATA | NODEFAULTLIBS 
             | OBJALIGN=n 
             | OLDLIBRARY=dll_name | ONEAUTODATA 
             | OSNAME='string' | PACKCODE=n | PACKDATA=n 
             | QUIET | REDEFSOK 
             | STACK=n | STATIC | STUB=stub_name 
             | SYMFILE[=symbol_file] | UNDEFSOK 
             | VERBOSE | VERSION=major[.minor] 

map_file is a file specification for the name of the map file.  If no file extension is specified, a file extension of "map" is assumed. 

symbol_file is a file specification for the name of the symbol file.  If no file extension is specified, a file extension of "sym" is assumed. 

module_name is the name of a program module or dynamic link library. 

dll_name is a file specification for the name of a dynamic link library.  If no file extension is specified, a file extension of "dll" is assumed. 

stub_name is a file specification for the name of the executable file.  If no file extension is specified, a file extension of "exe" is assumed. 

string is a sequence of characters. 

n represents a value.  The complete form of n is the following. 
    
   [0x]d{d}[k|m] 
d represents a decimal digit.  If 0x is specified, the string of digits represents a hexadecimal number.  If k is specified, the value is multiplied by 1024.  If m is specified, the value is multiplied by 1024*1024. 
The following sections describe the WATCOM Linker options specific to this executable format.  The options common to all executable formats are described in the chapter entitled General Directives and Options.


##### NT:  The ALIGNMENT Option

The "ALIGNMENT" option specifies the alignment for segments in the executable file.  The format of the "ALIGNMENT" option (short form "A") is as follows. 
    
     OPTION ALIGNMENT=n 

n represents a value.  The complete form of n is the following. 
    
   [0x]d{d}[k|m] 
d represents a decimal digit.  If 0x is specified, the string of digits represents a hexadecimal number.  If k is specified, the value is multiplied by 1024.  If m is specified, the value is multiplied by 1024*1024. 
n specifies the alignment for segments in the executable file and must be a power of 2. 
Segments in the executable file are pointed to by a segment table.  An entry in the segment table contains a 16-bit value which is a multiple of the alignment value.  Together they form the offset of the segment from the start of the segment table.  Note that the smaller the value of n the smaller the executable file. 
By default, the WATCOM Linker will automatically choose the smallest value of n possible.  You need not specify this option unless you want padding between segments in the executable file.


##### NT:  The DESCRIPTION Option

The "DESCRIPTION" option inserts the specified text into the application or dynamic link library.  This is useful if you wish to embed copyright information into an application or dynamic link library.  The format of the "DESCRIPTION" option (short form "DE") is as follows. 
    
     OPTION DESCRIPTION 'string' 

string is the sequence of characters to be embedded into the application or dynamic link library.


##### NT:  The HEAPSIZE Option

The "HEAPSIZE" option specifies the size of the heap required by the application.  The format of the "HEAPSIZE" option (short form "H") is as follows. 
    
     OPTION HEAPSIZE=n 

n represents a value.  The complete form of n is the following. 
    
   [0x]d{d}[k|m] 
d represents a decimal digit.  If 0x is specified, the string of digits represents a hexadecimal number.  If k is specified, the value is multiplied by 1024.  If m is specified, the value is multiplied by 1024*1024. 
n specifies the size of the heap.  The default heap size is 0 bytes.  The maximum value of n is 65536 (64K) for 16-bit applications and 4G for 32-bit applications which is the maximum size of a physical segment.  Actually, for a particular application, the maximum value of n is 64K or 4G less the size of group "DGROUP".


##### NT:  The MANYAUTODATA Option

The "MANYAUTODATA" option specifies that a copy of the automatic data segment (default data segment defined by the group "DGROUP"), for the program module or dynamic link library being created, is made for each instance.  The format of the "MANYAUTODATA" option (short form "MANY") is as follows. 
    
     OPTION MANYAUTODATA 
The default for a program module is "MANYAUTODATA" and for a dynamic link library is "ONEAUTODATA".


##### NT:  The MODNAME Option

The "MODNAME" option specifies a name to be given to the module being created.  The format of the "MODNAME" option (short form "MODN") is as follows. 
    
     OPTION MODNAME=module_name 

module_name is the name of a dynamic link library. 
Once a module has been loaded (whether it be a program module or a dynamic link library), mod_name is the name of the module known to Windows NT.  If the "MODNAME" option is not used to specify a module name, the default module name is the name of the executable file without the file extension.


##### NT:  The NOAUTODATA Option

The "NOAUTODATA" option specifies that no automatic data segment (default data segment defined by the group "DGROUP"), exists for the program module or dynamic link library being created.  The format of the "NOAUTODATA" option (short form "NOA") is as follows. 
    
     OPTION NOAUTODATA


##### NT:  The OBJALIGN Option

The "OBJALIGN" option specifies the alignment for objects in the executable file.  The format of the "OBJALIGN" option (short form "OBJA") is as follows. 
    
     OPTION OBJALIGN=n 

n represents a value.  The complete form of n is the following. 
    
   [0x]d{d}[k|m] 
d represents a decimal digit.  If 0x is specified, the string of digits represents a hexadecimal number.  If k is specified, the value is multiplied by 1024.  If m is specified, the value is multiplied by 1024*1024. 
n must be a value that is a power of 2 and is between 512 bytes and 256 megabytes inclusive.  The default is 64k.


##### NT:  The OLDLIBRARY Option

The "OLDLIBRARY" option is used to preserve the export ordinals for successive versions of a dynamic link library.  This ensures that any application that references functions in a dynamic link library by ordinal will continue to execute correctly.  The format of the "OLDLIBRARY" option (short form "OLD") is as follows. 
    
     OPTION OLDLIBRARY=dll_name 

dll_name is a file specification for the name of a dynamic link library.  If no file extension is specified, a file extension of "dll" is assumed. 
Only the current directory or a specified directory will be searched for dynamic link libraries specified in the "OLDLIBRARY" option.


##### NT:  The ONEAUTODATA Option

The "ONEAUTODATA" option specifies that the automatic data segment (default data segment defined by the group "DGROUP") for the program module or dynamic link library being created will be shared by all instances.  The format of the "ONEAUTODATA" option (short form "ONE") is as follows. 
    
     OPTION ONEAUTODATA 
The default for a dynamic link library is "ONEAUTODATA" and for a program module is "MANYAUTODATA".


##### NT:  The PACKDATA Option

By default, the WATCOM Linker automatically groups logical code segments into physical segments.  The "PACKDATA" option is used to specify the size of the physical segment.  The format of the "PACKCODE" option (short form "PACKD") is as follows. 
    
     OPTION PACKDATA=n 

n represents a value.  The complete form of n is the following. 
    
   [0x]d{d}[k|m] 
d represents a decimal digit.  If 0x is specified, the string of digits represents a hexadecimal number.  If k is specified, the value is multiplied by 1024.  If m is specified, the value is multiplied by 1024*1024. 
n specifies the size of the physical segments into which far data segments are packed.  The default value of n is 64K.  Note that this is also the maximum size of a physical segment.  To suppress automatic grouping of far data segments, specify a value of 0 for n. 
Notes: 

 1.Only adjacent segments are packed into a physical segment. 

 2.Segments belonging to the same group are packed in a physical segment.  Segments belonging to different groups are not packed into a physical segment. 

 3.Segments with different attributes are not packed together unless they are explicitly grouped.


##### NT:  The STUB Option

The "STUB" option specifies an executable file that is to be placed at the beginning of the Windows NT executable file being generated.  This program will be executed if the Windows NT module is executed under DOS.  The format of the "STUB" option is as follows. 
    
     OPTION STUB=stub_name 

stub_name is a file specification for the name of the stub executable file.  If no file extension is specified, a file extension of "exe" is assumed. 
The WATCOM Linker will search all paths specified in the "path" environment variable for the stub executable file.  The stub executable file specified by the "STUB" option must not be the same as the executable file being generated.


##### NT:  The VERSION Option

The "VERSION" option can be used to identify the application so that it can be distinguished from other versions (releases) of the same application.  This option is most useful when creating a DLL since applications that use the DLL may only execute with a specific version of the DLL. 
The format of the "VERSION" option (short form "VER") is as follows. 
    
     OPTION VERSION=major[.minor] 

major specifies the major version number. 

minor specifies the minor version number and must be less than 100.


#### NT:  The REFERENCE Directive

The "REFERENCE" directive is used to explicitly reference a symbol that is not referenced by any object file processed by the linker.  If any symbol appearing in a "REFERENCE" directive is not resolved by the linker, an error message will be issued for that symbol specifying that the symbol is undefined. 
The "REFERENCE" directive can be used to force object files from libraries to be linked with the application.  Also note that a symbol appearing in a "REFERENCE" directive will not be eliminated by dead code elimination.  For more information on dead code elimination, see the section entitled The ELIMINATE Option. 
The format of the "REFERENCE" directive (short form "REF") is as follows. 
    
     REFERENCE symbol_name{, symbol_name} 

symbol_name is the symbol for which a reference is made. 
Consider the following example. 
    
   reference domino 
The symbol domino will be searched for.  The object module that defines this symbol will be linked with the application.  Note that the linker will also attempt to resolve symbols referenced by this module.


#### NT:  The RUNTIME Directive

The "RUNTIME" directive specifies the environment under which the application will run.  The format of the "RUNTIME" directive (short form "R") is as follows. 
    
     RUNTIME  env 
     env ::= NATIVE | WINDOWS | CONSOLE | POSIX | OS2 | DOSSTYLE 
Specifying the "NATIVE" runtime option (short form "NAT") indicates that the application is a native Windows NT application. 
Specifying the "WINDOWS" runtime option (short form "WIN") indicates that the application is a Windows 3.x application. 
Specifying the "CONSOLE" runtime option (short form "CON") indicates that the application is a character-mode (command line oriented) application. 
Specifying the "POSIX" runtime option (short form "POS") indicates that the application uses the POSIX subsystem available with Windows NT. 
Specifying the "OS2" runtime option indicates that the application is a 16-bit OS/2 1.x application. 
Specifying the "DOSSTYLE" runtime option (short form "DOS") indicates that the application is a Phar Lap TNT DOS extender application that uses INT 21 to communicate to the DOS extender rather than calls to a DLL.


#### NT:  The SEGMENT Directive

The "SEGMENT" directive is used to describe the attributes of code and data segments.  The format of the "SEGMENT" directive (short form "SE") is as follows. 
    
     SEGMENT seg_desc{,seg_desc} 
     seg_desc ::= seg_id {seg_attrs}+ 
     seg_id ::= 'seg_name' | CLASS 'class_name' | TYPE [CODE | DATA] 
     seg_attrs ::= PAGEABLE | NONPAGEABLE 
               | SHARED | NONSHARED 

seg_name is the name of the code or data segment whose attributes are being specified. 

class_name is a class name.  The attributes will be assigned to all segments belonging to the specified class. 

PAGEABLE (short form "PAGE") specifies that the segment can be paged from memory.  This is the default. 

NONPAGEABLE (short form "NONP") specifies that the segment, once loaded into memory, must remain in memory. 

SHARED (short form "SH" ) specifies that a single copy of the segment will be loaded and will be shared by all processes. 

NONSHARED (short form "NONS") specifies that a unique copy of the segment will be loaded for each process.  This is the default. 
 Note:  Attributes specified for segments identified by a segment name override attributes specified for segments identified by a class name.


#### NT:  The SORT Directive

The "SORT" directive is used to sort the symbols in the "Memory Map" section of the map file.  By default, symbols are listed on a per module basis in the order the modules were encountered by the linker.  That is, a module header is displayed followed by the symbols defined by the module. 
The format of the "SORT" directive (short form "SO") is as follows. 
    
     SORT [GLOBAL] [ALPHABETICAL] 
If the "SORT" directive is specified without any options, as in the following example, the module headers will be displayed each followed by the list of symbols it defines sorted by address. 
    
   sort 
If only the "GLOBAL" sort option (short form "GL") is specified, as in the following example, the module headers will not be displayed and all symbols will be sorted by address. 
    
   sort global 
If only the "ALPHABETICAL" sort option (short form "ALP") is specified, as in the following example, the module headers will be displayed each followed by the list of symbols it defines sorted alphabetically. 
    
   sort alphabetical 
If both the "GLOBAL" and "ALPHABETICAL" sort options are specified, as in the following example, the module headers will not be displayed and all symbols will be sorted alphabetically. 
    
   sort global alphabetical 
If you are linking a WATCOM C++ application, mangled names are sorted by using the base name.  The base name is the name of the symbol as it appeared in the source file.  See the section entitled The MANGLEDNAMES Option for more information on mangled names.


### NT:  Memory Layout

The following describes the segment ordering of an application linked by the WATCOM Linker.  Note that this assumes that the "DOSSEG" linker option has been specified. 

 1.all segments not belonging to group "DGROUP" with class "CODE" 

 2.all other segments not belonging to group "DGROUP" 

 3.all segments belonging to group "DGROUP" with class "BEGDATA" 

 4.all segments belonging to group "DGROUP" not with class "BEGDATA", "BSS" or "STACK" 

 5.all segments belonging to group "DGROUP" with class "BSS" 

 6.all segments belonging to group "DGROUP" with class "STACK" 
A special segment belonging to class "BEGDATA" is defined when linking with WATCOM run-time libraries.  This segment is initialized with the hexadecimal byte pattern "01" and is the first segment in group "DGROUP" so that storing data at location 0 can be detected. 
Segments belonging to class "BSS" contain uninitialized data.  Note that this only includes uninitialized data in segments belonging to group "DGROUP".  Segments belonging to class "STACK" are used to define the size of the stack used for your application.  Segments belonging to the classes "BSS" and "STACK" are last in the segment ordering so that uninitialized data need not take space in the executable file.


### NT:  The WATCOM Linker Memory Requirements

The WATCOM Linker uses all available memory when linking an application.  For DOS-hosted versions of the WATCOM Linker, this includes expanded memory (EMS) and extended memory.  It is possible for the size of the image being linked to exceed the amount of memory available in your machine, particularly if the image file is to contain debugging information. For this reason, a temporary disk file is used when all available memory is used by the WATCOM Linker. 
Normally, the temporary file is created in the default directory.  However, by defining the "tmp" environment variable to be a directory, you can tell the WATCOM Linker where to create the temporary file.  This can be particularly useful if you have a RAM disk.  Consider the following definition of the "tmp" environment variable. 
    
   set tmp=\tmp 
The WATCOM Linker will create the temporary file in the directory "\tmp".


## Linker Error Messages

The WATCOM Linker issues three classes of messages; fatal errors, errors and warnings.  Each message has a 4-digit number associated with it.  Fatal messages start with the digit 3, error messages start with the digit 2, and warning messages start with the digit 1.  It is possible for a message to be issued as a warning or an error. 
If a fatal error occurs, the linker will terminate immediately and no executable file will be generated. 
If an error occurs, the linker will continue to execute so that all possible errors are issued.  However, no executable file will be generated since these errors do not permit a proper executable file to be generated. 
If a warning occurs, the linker will continue to execute.  A warning message is usually informational and does not prevent the creation of a proper executable file.  However, all warnings should eventually be corrected. 
The messages listed contain references to %s, %S, %a, %x, %d, and %l.  They represent strings that are substituted by the WATCOM Linker to make the error message more precise. 

 1. %s represents a string.  This may be a segment or group name, or the name of a linker directive or option. 

 2. %S represents the name of a symbol. 

 3. %a represents an address.  The format of the address depends on the format of the executable file being generated. 

 4. %x represents a hexadecimal number. 

 5. %d represents integers in the range -32768 and 32767. 

 6. %l represents integers in the range -2147483648 and 2147483647. 
The following is a list of all warning and error messages produced by the WATCOM Linker followed by a description of the message.  A message may contain more than one reference to "%s".  In such a case, the description will reference them as "%sn" where n is the occurrence of "%s" in the message.


### 2002 ** internal ** - %s

2002 ** internal ** - %s 
If this message occurs, you have found a bug in the WATCOM Linker and should contact WATCOM.


### 2008 cannot open %s :  %s

2008 cannot open %s :  %s 
An error occurred while trying to open the file "%s1".  The reason for the error is given by "%s2".  Generally this error message is issued when the WATCOM Linker cannot open an object file or directive file.


### 3009 dynamic memory exhausted

3009 dynamic memory exhausted 
The WATCOM Linker uses all available memory when linking an application.  For DOS-hosted versions of the WATCOM Linker, this includes expanded memory (EMS) and extended memory.  When all available memory is used, a spill file will be used.  Therefore, unless you are low on disk space, the WATCOM Linker will always be able to generate the executable file.  Dynamic memory is the memory the WATCOM Linker uses to build its internal data structures and symbol table.  Dynamic memory is the amount of conventional memory (below 1 megabyte) available on your machine; a spill file is not used for dynamic memory.  If the WATCOM Linker issues this message, it cannot link your application.  The following are suggestions that may help you in this situation. 

 1.Concatenate all your object files into one and specify only the resulting object file as input to the WATCOM Linker.  For example, if you are linking in a DOS environment, you can issue the following DOS command. 
    
   C>copy/b *.obj all.obj 
This significantly reduces the size of the file list the WATCOM Linker must maintain. 

 2.Object files may contain a record which specifies the module name.  This information is used by WATCOM Debugger to locate modules during a debugging session and usually contains the full path of the source file.  This can consume a significant amount of memory when many such object files are being linked.  If your source is being compiled by the WATCOM C compiler, you can use the "nm" option to set the module name to just the file name.  This reduces the amount of memory required by the WATCOM Linker.  If your are using WATCOM Debugger to debug your application, you may have to use the "set source" command so that the source corresponding to a module can be located. 

 3.Typically, when you are compiling a program for a large code model, each module defines a different "text" segment.  If you are compiling your application using the WATCOM C compiler, you can reduce the number of "text" segments that the WATCOM Linker has to process by specifying the "nt" option.  The "nt" option allows you to specify the name of the "text" segment so that a group of object files define the same "text" segment.


### 2010,3010 I/O error processing %s :  %s

2010,3010 I/O error processing %s :  %s 
An error has occurred while processing the file "%s1".  The cause of the error is given by "%s2".  This error is usually detected while reading from object and library files or writing to the spill file or executable file.  For example, this error would be issued if a "disk full" condition existed.


### 2011 invalid object file attribute

2011 invalid object file attribute 
The WATCOM Linker encountered an object file that was not of the format required of an object file.


### 2012 invalid library file attribute

2012 invalid library file attribute 
The WATCOM Linker encountered a library file that was not of the format required of a library file.


### 3013 break key detected

3013 break key detected 
The linking process was interrupted by the user from the keyboard.


### 1014 stack segment not found

1014 stack segment not found 
The WATCOM Linker identifies the stack segment by a segment defined as having the "STACK" attribute.  This message is issued if no such segment is encountered.  This usually happens if the WATCOM Linker cannot find the run-time libraries required to link your application.


### 2015 bad location specified in FIXUP

2015 bad location specified in FIXUP 
This message is issued if a bad object file is encountered.


### 2016 %a:  absolute target invalid for self-relative relocation

2016 %a:  absolute target invalid for self-relative relocation 
This message is issued, for example, if a near call or jump is made to an external symbol which is defined using the "EQU" assembler directive.  "%a" identifies the location of the near call or jump instruction.


### 2017 bad location specified for self-relative relocation at %a

2017 bad location specified for self-relative relocation at %a 
This message is issued if a bad fixup is encountered.  "%a" defines the location of the fixup.


### 2018 relocation offset at %a is out of range

2018 relocation offset at %a is out of range 
This message is issued when the offset part of a relocation exceeds 64K.  "%a" defines the location of the fixup.  The error is most commonly caused by errors in coding assembly language routines.  Consider a module that references an external symbol that is defined in a segment different from the one in which the reference occurred.  The module, however, specifies that the segment in which the symbol is defined is the same segment as the segment that references the symbol.  This error is most commonly caused when the "EXTRN" assembler directive is placed after the "SEGMENT" assembler directive for the segment referencing the symbol.  If the segment that references the symbol is allocated far enough away from the segment that defines the symbol, the WATCOM Linker will issue this message.


### 1019 segment relocation at %a

1019 segment relocation at %a 
This message is issued when a segment relocation is encountered and "FORMAT DOS COM", "FORMAT PHARLAP" or "FORMAT NOVELL" has been specified.  None of the above executable file formats allow segment relocation.  "%a" identifies the location of the segment relocation.


### 2020 size of group %s exceeds 64k by %l bytes

2020 size of group %s exceeds 64k by %l bytes 
The group "%s" has exceeded the maximum size (64k) allowed for a group by "%l" bytes.  Usually, the group is "DGROUP" (the default data segment) and your application has placed too much data in this group.  One of the following may solve this problem. 

 1.If you are using the WATCOM C compiler, you can place some of your data in a far segment by using the "far" keyword when defining data.  You can also decrease the value of the data threshold by using the "zt" compiler option.  Any datum whose size exceeds the value of the data threshold will be placed in a far segment. 

 2.If you are using the WATCOM FORTRAN 77 compiler, you can decrease the value of the data threshold by using the "dt" compiler option.  Any datum whose size exceeds the value of the data threshold will be placed in a far segment.


### 2021 size of segment %s exceeds 64k by %l bytes

2021 size of segment %s exceeds 64k by %l bytes 
The segment "%s" has exceeded the maximum size (64k) of a segment.  This usually occurs if you are linking an application that has been compiled for a small code model and the size of the application has grown in such a way that the size of the code segment ("_TEXT") has exceeded 64k.  You can overlay your application or compile it for a large code model if you cannot reduce the amount of code in your application.


### 2022 cannot have a starting address with an imported symbol

2022 cannot have a starting address with an imported symbol 
When generating an OS/2 executable file, a symbol imported from a DLL cannot be a start address.  When generating a NetWare 386 executable file, a symbol imported from an NLM cannot be a start address.


### 1023 no starting address found, using %a

1023 no starting address found, using %a 
The starting address defines the location where execution is to begin and must be defined by a special "module end" record in one of the object files linked into your application.  This message is issued if no such record is encountered in which case a default starting address, namely "%a", will be used.  This usually happens if the WATCOM Linker cannot find the run-time libraries required to link your application.


### 2024 missing overlay loader

2024 missing overlay loader 
This message is issued when an overlayed application is being linked and the overlay manager has not been encountered.  This usually happens if the WATCOM Linker cannot find the run-time libraries required to link your application.


### 2025 short vector %d is out of range

2025 short vector %d is out of range 
This message is issued when the WATCOM Linker is creating an overlayed application and "OPTION SMALL" is specified.  Since an overlay vector contains a near call to the overlay loader followed by a near jump to the routine corresponding to the overlay vector, all code including the overlay manager and all overlay vectors must be less than 64K.  This message is issued if the offset of an overlay vector from the overlay loader or the corresponding routine exceeds 64K.


### 2026 redefinition of reserved symbol %s

2026 redefinition of reserved symbol %s 
The WATCOM Linker defines certain reserved symbols.  These symbols are "_edata", "_end", "__OVLTAB__", "__OVLSTARTVEC__", "__OVLENDVEC__", "__LOVLLDR__", "__NOVLLDR__", "__SOVLLDR__", "__LOVLINIT__", "__NOVLINIT__" and "__SOVLINIT__".  The symbols "__OVLTAB__", "__OVLSTARTVEC__", "__OVLENDVEC__", "__LOVLLDR__", "__NOVLLDR__", "__SOVLLDR__", "__LOVLINIT__", "__NOVLINIT__" and "__SOVLINIT__" are defined only if you are using overlays.  The symbols "_edata" and "_end" are defined only if the "DOSSEG" option is specified.  Your application must not attempt to define these symbols.  "%s" identifies the reserved symbol.


### 1027 redefinition of %S ignored

1027 redefinition of %S ignored 
The symbol "%S" has been defined by more that one module; the first definition is used.  This is only a warning message.  Note that if a symbol is defined more than once and its address is the same in both cases, no warning will be issued.  This prevents the warning message from being issued when linking FORTRAN 77 modules that contain common blocks.


### 1028 %S is an undefined reference

1028 %S is an undefined reference 
The symbol "%S" has been referenced but not defined.  Check that the spelling of the symbol is consistent.  If you wish the linker to ignore undefined references, use the "UNDEFSOK" option.


### 2029 premature end of file encountered

2029 premature end of file encountered 
This error is issued while processing object files and object modules from libraries and is caused if the end of the file or module is reached before the "module end" record is encountered.  The probable cause is a truncated object file.


### 2030 multiple starting addresses found

2030 multiple starting addresses found 
The starting address defines the location where execution is to begin and is defined by a "module end" record in a particular object file.  This message is issued if more than one object file contains a "module end" record that defines a starting address.


### 2031 segment %s is in group %s and group %s

2031 segment %s is in group %s and group %s 
The segment "%s1" has been defined to be in group "%s2" in one module and in group "%s3" in another module. A segment can only belong to one group.


### 1032 record (type 0x%x) not processed

1032 record (type 0x%x) not processed 
An object record type not supported by the WATCOM Linker has been encountered.  This message is issued when linking object modules created by other compilers or assemblers that create object files with records that the WATCOM Linker does not support.


### 2033,3033 directive error near '%s'

2033,3033 directive error near '%s' 
A syntax error occurred while the WATCOM Linker was processing directives.  "%s" specifies where the error occurred.


### 2034 %a cannot have an offset with an imported symbol

2034 %a cannot have an offset with an imported symbol 
An imported symbol is one that was specified in an "IMPORT" directive.  For example, under OS/2 imported symbols are defined in DLLs.  References to imported symbols must always have an offset value of 0.  If "DosWrite" is an imported symbol, then referencing "DosWrite+2" is illegal.  "%a" defines the location of the illegal reference.


### 1038 DEBUG directive appears after object files

1038 DEBUG directive appears after object files 
This message is issued if the first "DEBUG" directive appears after a "FILE" directive.  A common error is to specify a "DEBUG" directive after the "FILE" directives in which case no debugging information for those object files is generated in the executable file.


### 2039 ALIGNMENT value too small

2039 ALIGNMENT value too small 
The value specified in the "ALIGNMENT" option refers to the alignment of segments in the executable file.  Segments in the executable file are pointed to by a segment table.  An entry in the segment table contains a 16-bit value which is a multiple of the alignment value.  Together they form the offset of the segment from the start of the segment table.  The smaller the alignment, the bigger the value required in the segment table to point to the segment.  If this value exceeds 64k, then a larger alignment value is required to decrease the size that goes in the segment table.


### 2040 ordinal in IMPORT directive not valid

2040 ordinal in IMPORT directive not valid 
The specified ordinal in the "IMPORT" directive is incorrect (e.g., -1).  An ordinal number must be in the range 0 to 65535.


### 2041 ordinal in EXPORT directive not valid

2041 ordinal in EXPORT directive not valid 
The specified ordinal in the "EXPORT" directive is incorrect (e.g., -1).  An ordinal number must be in the range 0 to 65535.


### 2042 too many IOPL words in EXPORT directive

2042 too many IOPL words in EXPORT directive 
The maximum number of IOPL words is 63.


### 1043 duplicate exported ordinal

1043 duplicate exported ordinal 
This message is issued for ordinal numbers specified in an "EXPORT" directive for symbols belonging to OS/2 DLLs.  This message is issued if an ordinal number is assigned to two different symbols.  A warning is issued and the WATCOM Linker assigns a non-used ordinal number to the symbol that caused the warning.


### 1044,2044 exported symbol %s not found

1044,2044 exported symbol %s not found 
This message is issued when generating OS/2 DLLs and NetWare 386 NLMs.  An attempt has been made to define an entry point into a DLL or NLM that does not exist.


### 1045 segment attribute defined more than once

1045 segment attribute defined more than once 
A segment appearing in a "SEGMENT" directive has been given conflicting or duplicate attributes.


### 1046 segment name %s not found

1046 segment name %s not found 
The segment name specified in a "SEGMENT" directive has not been defined.


### 1047 class name %s not found

1047 class name %s not found 
The class name specified in a "SEGMENT" directive has not been defined.


### 1048 inconsistent attributes for automatic data segment

1048 inconsistent attributes for automatic data segment 
This message is issued for OS/2 executable files.  Two conflicting attributes were specified for the automatic data segment.  For example, "LOADONCALL" and "PRELOAD" are conflicting attributes.  Only the first attribute is used.


### 2049 invalid STUB file

2049 invalid STUB file 
The stub file is not a valid executable file.  The stub file is only used for OS/2 executable files.


### 1050 invalid DLL specified in OLDLIBRARY option

1050 invalid DLL specified in OLDLIBRARY option 
The OS/2 DLL specified in an "OLDLIBRARY" option is not a valid dynamic link library.


### 2051 STUB file name same as executable file name

2051 STUB file name same as executable file name 
When generating an OS/2 executable file, the stub file name must not be same as the executable file name.


### 2052 relocation at %a not in the same segment

2052 relocation at %a not in the same segment 
This message is only issued for protected-mode applications.  A relative fixup must relocate to the same segment.  "%a" defines the location of the fixup.


### 2053 %a:  cannot reach a DLL with a relative relocation

2053 %a:  cannot reach a DLL with a relative relocation 
A reference to a symbol in an OS/2 DLL must not be relative.  "%a" defines the location of the reference.


### 1054 debugging information incompatible:  using line numbers only

1054 debugging information incompatible:  using line numbers only 
An attempt has been made to link an object file with out-of-date debugging information.


### 2055 %a:  frame must be the same as the target in protected mode

2055 %a:  frame must be the same as the target in protected mode 
Each relocation consists of three components; the location being relocated, the target (or address being referenced), and the frame (the segment to which the target is adjusted).  In protected mode, the segment of the target must be the same as the frame.  "%a" defines the location of the fixup.


### 2056 cannot find library member %s(%s)

2056 cannot find library member %s(%s) 
Library member "%s2" in library file "%s1" could not be found.  This message is issued if the library file could not be found or the library file did not contain the specified member.


### 3057 executable format has been established

3057 executable format has been established 
This message is issued if there is more than one "FORMAT" directive.


### 1058 %s option not valid for %s executable

1058 %s option not valid for %s executable 
The option "%s1" can only be specified if an executable file whose format is "%s2" is being generated.


### 1059,2059 value for %s too large

1059,2059 value for %s too large 
The value specified for option "%s" exceeds its limit.


### 1060 value for %s incorrect

1060 value for %s incorrect 
The value specified for option "%s" is not in the allowable range.


### 1061 multiple values specified for REALBREAK

1061 multiple values specified for REALBREAK 
The "REALBREAK" option can only be specified once.


### 1062 DLL COMENT record invalid when not in OS2

1062 DLL COMENT record invalid when not in OS2 
A DLL COMENT record contains information for symbols that are defined in dynamic link libraries.  This message is issued if a reference to a DLL is encountered and the executable file format is not "OS2".


### 2063 invalid relocation for flat memory model at %a

2063 invalid relocation for flat memory model at %a 
A segment relocation in the flat memory model was encountered.  "%a" defines the location of the fixup.


### 2064 cannot combine 32-bit segments with 16-bit segments

2064 cannot combine 32-bit segments with 16-bit segments 
A 16-bit segment and a 32-bit segment have been encountered.  Mixing object files created by a 286 compiler and object files created by a 386 compiler is the most probable cause of this error.


### 2065 REALBREAK symbol %s not found

2065 REALBREAK symbol %s not found 
The symbol specified in the "REALBREAK" option has not been defined.


### 2066 invalid relative relocation type for an import at %a

2066 invalid relative relocation type for an import at %a 
This message is issued only if a NetWare 386 executable file is being generated.  An imported symbol is one that was specified in an "IMPORT" directive.  Any reference to an imported symbol must not refer to the segment of the imported symbol.  "%a" defines the location of the reference.


### 2067 %a:  cannot relocate between code and data in Novell formats

2067 %a:  cannot relocate between code and data in Novell formats 
This message is issued only if a NetWare 386 executable file is being generated.  Segment relocation is not permitted.  "%a" defines the location of the fixup.


### 2068 absolute segment fixup not valid in protected mode

2068 absolute segment fixup not valid in protected mode 
A reference to an absolute location is not allowed in protected mode.  A protected-mode application is one that is being generated for OS/2, FlashTek's DOS extender, Phar Lap's 386|DOS-Extender, Tenberry Software's DOS/4G, or Novell's NetWare 386 operating system.  An absolute location is most commonly defined by the "EQU" assembler directive.


### 1069 unload CHECK procedure not found

1069 unload CHECK procedure not found 
The symbol specified in the "CHECK" option has not been defined.


### 2070 START procedure not found

2070 START procedure not found 
The symbol specified in the "START" option has not been defined.  The default "START" symbol is "_Prelude".


### 2071 EXIT procedure not found

2071 EXIT procedure not found 
The symbol specified in the "EXIT" option has not been defined.  The default "STOP" symbol is "_Stop".


### 1072 SECTION directive not allowed in root

1072 SECTION directive not allowed in root 
"SECTION" directives must appear between a "BEGIN" directive and its corresponding "END" directive.


### 2073 bad Novell file format specified

2073 bad Novell file format specified 
An invalid NetWare 386 executable file format was specified.  Valid formats are NLM, DSK, NAM and LAN.


### 2074 invalid NLM description

2074 invalid NLM description 
The description specified in the "FORMAT NOVELL" directive has not been, or is incorrectly, specified.


### 2075 expecting an END directive

2075 expecting an END directive 
A "BEGIN" directive is missing its corresponding "END" directive.


### 1076 %s option multiply specified

1076 %s option multiply specified 
The option "%s" can only be specified once.


### 1080 file %s is a 32-bit object file

1080 file %s is a 32-bit object file 
A 32-bit attribute was encountered while generating a 16-bit executable file format.


### 2082 invalid record type 0x%x

2082 invalid record type 0x%x 
An object record type not recognized by the WATCOM Linker has been encountered.  This message is issued when linking object modules created by other compilers or assemblers that create object files with records that the WATCOM Linker does not recognize.


### 2083 cannot reference address %a from frame %x

2083 cannot reference address %a from frame %x 
The offset of a referenced symbol is greater than 64k from the location referencing it.


### 2084 target offset exceeds 64K at %a

2084 target offset exceeds 64K at %a 
The computed offset for a symbol exceeds 64k.  "%a" defines the location of the fixup.


### 2086 invalid starting address for .COM file

2086 invalid starting address for .COM file 
The value of the segment of the starting address for a DOS "COM" file, as specified in the map file, must be 0.


### 1087 stack segment ignored in .COM file

1087 stack segment ignored in .COM file 
A stack segment must not be defined when generating a DOS "COM" file.  Only a single physical segment is allowed in a DOS "COM" file.  The stack is allocated from the high end of the physical segment.  That is, the initial value of SP is hexadecimal fffe.


### 3088 virtual memory exhausted

3088 virtual memory exhausted 
This message is similar to the "dynamic memory exhausted" message.  The WATCOM Linker has run out of memory trying to keep track of virtual memory blocks.  Virtual memory blocks are allocated from expanded memory, extended memory and the spill file.


### 2089 program too large for a .COM file

2089 program too large for a .COM file 
The total size of a DOS "COM" program must not exceed 64K.  That is, the total amount of code and data must be less than 64K since only a single physical segment is allowed in a DOS "COM" file.  You must decrease the size of your program or generate a DOS "EXE" file.


### 1090 redefinition of %s by %s ignored

1090 redefinition of %s by %s ignored 
The symbol "%s1" has been redefined by module "%s2".  This message is issued when the size specified in the "NAMELEN" option has caused two symbols to map to the same symbol.  For example, if the symbols routine1 and routine2 are encountered and "OPTION NAMELEN=7" is specified, then this message will be issued since the first seven characters of the two symbols are identical.


### 2091 group %s is in more than one overlay

2091 group %s is in more than one overlay 
A group that spans more than one section has been detected.


### 2092 NEWSEGMENT directive appears before object files

2092 NEWSEGMENT directive appears before object files 
The "NEWSEGMENT" option must appear after a "FILE" directive.


### 2093 cannot open %s

2093 cannot open %s 
This message is issued when the WATCOM Linker is unable to open a file and is unable to determine the cause.


### 2094 i/o error processing %s

2094 i/o error processing %s 
This message is issued when the WATCOM Linker has encountered an i/o error while processing the file and is unable to determine the cause.  This message may be issued when reading from object and library files, or writing to the executable and spill file.


### 1095 debugging information too large.

1095 debugging information too large. 
This message is only issued when linking an application that has been compiled with version 9.0 of the compiler or earlier.  Later versions of the compiler have removed this limit.


### 3096 incompatible types of debugging information found

3096 incompatible types of debugging information found 
The WATCOM Linker has encountered more than one class of debugging information in the object files it is processing (e.g., Codeview and WATCOM).


### 3097 too many library modules

3097 too many library modules 
This message is similar to the "dynamic memory exhausted" message.  This message if issued when the "DISTRIBUTE" option is specified.  The WATCOM Linker has run out of memory trying to keep track of the relationship between object modules extracted from libraries and the overlays they should be placed in.


### 1098 Phar Lap offset option must be a multiple of 4K

1098 Phar Lap offset option must be a multiple of 4K 
The value specified with the "OFFSET" option must be a multiple of 4096.


### 2099 symbol name too long:  %s

2099 symbol name too long:  %s 
The maximum size (approximately 2048) of a symbol has been exceeded.  Reduce the size of the symbol to avoid this error.


### 1101 cannot use both option verbose and a trace directive

1101 cannot use both option verbose and a trace directive 
The "VERBOSE" option cannot be used in conjunction with the "SYMTRACE" and "MODTRACE" directives.


### 1102 object file %s not found for tracing

1102 object file %s not found for tracing 
A "SYMTRACE" or "MODTRACE" directive contained an object file (namely %s) that could not be found.


### 1103 library module %s(%s) not found for tracing

1103 library module %s(%s) not found for tracing 
A "SYMTRACE" or "MODTRACE" directive contained an object module (namely module %s1 in library %s2 ) that could not be found.


### 1105 cannot reserve %l bytes of extra overlay space

1105 cannot reserve %l bytes of extra overlay space 
The value specified with the "AREA" option results in an executable file that requires more than 1 megabyte of memory to execute.


### 1107 undefined system name:  %s

1107 undefined system name:  %s 
The name %s was referenced in a "SYSTEM" directive but never defined by a system block definition.


### 1108 system %s defined more than once

1108 system %s defined more than once 
The name %s has appeared in a system definition block more than once.


### 3109 system block %s too large

3109 system block %s too large 
The largest size of a system definition block is 4K.  This message will be issued if the total amount of text specified in the system definition block exceeds this limit.


### 1110 library members not allowed in libfile

1110 library members not allowed in libfile 
Only object files are allowed in a "LIBFILE" directive.  This message will be issued if a module from a library file is specified in a "LIBFILE" directive.


### 1111 error in default system block

1111 error in default system block 
The default system block definition (system name "286" for 16-bit applications) and (system name "386" for 32-bit applications) contains a directive error.  The system name "286" or "386" is automatically referenced by the linker when the format of the executable cannot be determined (i.e.  no "FORMAT" directive has been specified).


### 3114 environment name specified incorrectly

3114 environment name specified incorrectly 
This message is specified if the environment variable is not properly enclosed between two percent (%) characters.


### 1115 environment name %s not found

1115 environment name %s not found 
The environment variable %s has not been defined in the environment space.


### 1116 overlay area must be at least %l bytes

1116 overlay area must be at least %l bytes 
This message is issued if the size of the largest overlay exceeds the size of the overlay area specified by the "AREA" option.


### 1117 segment number too high for a movable entry point

1117 segment number too high for a movable entry point 
The segment number of a moveable segment must not exceed 255.  Reduce the number of segments or use the "PACKCODE" option.


### 1118 heap size too large

1118 heap size too large 
This message is issued if the size of the heap, stack and the default data segment (group DGROUP) exceeds 64K.


### 2119 wlib import statement incorrect

2119 wlib import statement incorrect 
The "EXPORT" directive allows you to specify a library command file.  This command file is scanned for any librarian commands that create import library entries.  An invalid command was detected.  See the section entitled "The EXPORT Directive" for the correct format of these commands.


### 2120 application too large to run under DOS

2120 application too large to run under DOS 
This message is issued if the size of the DOS application exceeds 1M.


### 1121 '%s' has already been exported

1121 '%s' has already been exported 
The linker has detected an attempt to export a symbol more than once.  For example, a name appearing in more than one "EXPORT" directive will cause this message to be issued.  Also, if you have declared a symbol as an export in your source and have also specified the same symbol in an "EXPORT" directive, this message will be issued.  This message is only a warning.


### 3122 no FILE directives found

3122 no FILE directives found 
This message is issued if no "FILE" directive has been specified.  In other words, you have specified no object files to link.


### 3123 OS/2 offset option must be a multiple of 64K

3123 OS/2 offset option must be a multiple of 64K 
The value specified with the "OFFSET" option for OS/2 2.x must be a multiple of 64K.


### 1124 lazy reference for %S has different default resolutions

1124 lazy reference for %S has different default resolutions 
A lazy external reference is one which has two resolutions:  a preferred one and a default one which is used if the preferred one is not found.  In this case, the linker has found two lazy references that have the same preferred resolution but different default resolutions.


### 1125 multiple aliases found for %S

1125 multiple aliases found for %S 
The linker has found a name which has been aliased to two different symbols.


### 1126 INT 15 interrupt may be incorrect

1126 INT 15 interrupt may be incorrect 
An error was reported while the linker was trying to access extended memory.  The interrupt 15 vector (used to access extended memory) has been corrupted during the linking process.


### 3126 too many EMS requests queued

3126 too many EMS requests queued 
An error was reported while the linker was trying to access expanded memory.  The error message is issued if too many applications are simultaneously making extended memory requests.  EMS physical mapping corrupted 
A serious problem has occurred while trying to access expanded memory.  The EMS frame has been corrupted.  This can be caused by a TSR that is using the EMS frame for other reasons.


### 2127 cannot export absolute symbol %S

2127 cannot export absolute symbol %S 
An attempt was made to export a symbol defined with an absolute address.  It is not possible to export a symbol with an absolute address using the "EXPORT" directive.


### 3128 directive error near beginning of input

3128 directive error near beginning of input 
The linker detected an error at the start of the command line.


### 3129 address information too large

3129 address information too large 
The linker has encountered a segment that appears in more than 11000 object files.  An empty segment does not affect this limit.


### 1130 %s is an invalid shared nlm file

1130 %s is an invalid shared nlm file 
The NLM specified in a "SHAREDNLM" option is not valid.


### 3131 cannot open spill file:  file already exists

3131 cannot open spill file:  file already exists 
All 26 of the linker's possible spill file names are in use.  Spill files can accumulate when linking on a multi-tasking system and the directory in which the spill file is created is identical for each invocation of the linker.


### 2132 curly brace delimited list incorrect

2132 curly brace delimited list incorrect 
A list delimited by curly braces is not correct.  The most likely cause is a missing right brace.


### 1133 no realbreak specified for 16-bit code

1133 no realbreak specified for 16-bit code 
While generating a Phar Lap executable file, both 16-bit and 32-bit code was linked together and no "REALBREAK" option has been specified.  A warning message is issued since this may be a potential problem.


### 1134 %s is an invalid message file

1134 %s is an invalid message file 
The file specified in a "MESSAGE" option for NetWare 386 executable files is invalid.


### 3135 need exactly 1 overlay area with dynamic overlay manager

3135 need exactly 1 overlay area with dynamic overlay manager 
Only a single overlay area is supported by the dynamic overlay manager.


### 1136 relocation to a read/write data segment found at %a

1136 relocation to a read/write data segment found at %a 
The "RWRELOCCHECK" option has been specified and the linker has detected a segment relocation to a read/write data segment.


### 3137 too many errors encountered

3137 too many errors encountered 
This message is issued when the number of error messages issued by the linker exceeds the number specified by the "MAXERRORS" option.


### 3138 invalid filename '%s'

3138 invalid filename '%s' 
The linker performs a simple filename validation whenever a filename is specified to the linker.  For example, a directory specification is not a valid filename.


### 3139 cannot have both 16-bit and 32-bit object files

3139 cannot have both 16-bit and 32-bit object files 
It is impossible to mix 16-bit code and 32-bit code in the same executable when generating a QNX executable file.


### 1140 invalid message number

1140 invalid message number 
An invalid message number has been specified in a "DISABLE" directive.


### 1141 virtual function table record for %s mismatched

1141 virtual function table record for %s mismatched 
This is a consistency check by the linker to ensure that the WATCOM C++ compiler has not generated incorrect virtual function information.  Contact WATCOM if this message is issued.


### 1143 not enough memory to sort map file symbols

1143 not enough memory to sort map file symbols 
There was not enough memory for the linker to sort the symbols in the "Memory Map" portion of the map file. This will only occur when "GLOBAL" sort option has been specified.


### 1145 %S is both pure virtual and non-pure virtual

1145 %S is both pure virtual and non-pure virtual 
A function has been declared both as "pure" and "non-pure" virtual.


### 2146 %s is an invalid object file

2146 %s is an invalid object file 
Something was encountered in the object that cannot be processed by the linker.


### 3147 Ambiguous format specified

3147 Ambiguous format specified 
Not enough of the FORMAT directive attributes were specified to enable the linker to determine the executable file format.  For example, 
    
   FORMAT OS2 
will generate this message.


### 1148 Invalid segment type specified

1148 Invalid segment type specified 
The segment type must be one of CODE or DATA.


### 1149 Only one debugging format can be specified

1149 Only one debugging format can be specified 
The debugging format must be one of WATCOM (default), Codeview, or Dwarf.  You cannot specify additional debugging formats.
