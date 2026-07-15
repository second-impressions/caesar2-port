# C Library Reference


## Index of Topics


## C Library Overview

The C library provides much of the power usually associated with the C language.  This chapter introduces the individual functions (and macros) that comprise the WATCOM C library for DOS, Microsoft Windows, and OS/2.  The chapter Library Functions and Macros describes each function and macro in complete detail. 
Library functions are called as if they had been defined within the program.  When the program is linked, the code for these routines is incorporated into the program by the linker. 
Strictly speaking, it is not necessary to declare most library functions since they return int values for the most part.  It is preferred, however, to declare all functions by including the header files found in the synopsis section with each function.  Not only does this declare the return value, but also the type expected for each of the arguments as well as the number of arguments.  This enables the WATCOM C compiler to check the arguments coded with each function call.


### Classes of Functions

The functions in the WATCOM C library can be organized into a number of classes: 

Character Manipulation Functions 
These functions deal with single characters. 

Memory Manipulation Functions 
These functions manipulate blocks of memory. 

String Manipulation Functions 
These functions manipulate strings of characters.  A character string is an array of zero or more adjacent characters followed by a null character ('\0') which marks the end of the string. 

Multibyte Character Functions 
These ANSI C functions provide capabilities for processing multibyte and wide characters. 

Conversion Functions 
These functions convert values from one representation to another.  Numeric values, for example, can be converted to strings. 

Memory Allocation Functions 
These functions are concerned with allocating and deallocating memory. 

Heap Functions 
These functions provide the ability to shrink and grow the heap, as well as, find heap related problems. 

Math Functions 
The mathematical functions perform mathematical computations such as the common trigonometric calculations. These functions operate on double values, also known as floating-point values. 

Searching Functions 
These functions provide searching and sorting capabilities. 

Time Functions 
These functions provide facilities to obtain and manipulate times and dates. 

Variable-length Argument Lists 
These functions provide the capability to process a variable number of arguments to a function. 

Stream I/O Functions 
These functions provide the "standard" functions to read and write files.  Data can be transmitted as characters, strings, blocks of memory or under format control. 

Process Primitive Functions 
These functions deal with process creation, execution and termination, signal handling, and timer operations. 

Process Environment 
These functions deal with process identification, user identification, process groups, system identification, system time and process time, environment variables, terminal identification, and configurable system variables. 

Directory Functions 
These functions provide directory services. 

Operating System I/O Functions 
These "non-standard" file operations are more primitive than the "standard" functions in that they are directly interfaced to the operating system.  They are included to provide compatibility with other C implementations and to provide the capability to directly use operating-system file operations. 

File Manipulation Functions 
These functions operate directly on files, providing facilities such as deletion of files. 

Console I/O Functions 
These functions provide the capability to directly read and write characters from the console. 

Default Windowing Functions 
These functions provide the capability to manipulate various dialog boxes in WATCOM's default windowing system. 

BIOS Functions 
This set of functions allows access to services provided by the BIOS. 

DOS-Specific Functions 
This set of functions allows access to DOS-specific functions. 

Intel 80x86 Architecture-Specific Functions 
This set of functions allows access to Intel 80x86 processor-related functions. 

Miscellaneous Functions 
This collection consists of the remaining functions. 
The following subsections describe these function classes in more detail.  Each function in the class is noted with a brief description of its purpose.  The chapter Library Functions and Macros provides a complete description of each function and macro.


#### Character Manipulation Functions

These functions operate upon single characters of type char.  The functions test characters in various ways and convert them between upper and lowercase.  The following functions are defined: 

isalnum test for letter or digit 

isalpha test for letter 

isascii test for ASCII character 

iscntrl test for control character 

isdigit test for digit 

isgraph test for printable character, except space 

islower test for letter in lowercase 

isprint test for printable character, including space 

ispunct test for punctuation characters 

isspace test for white space characters 

isupper test for letter in uppercase 

isxdigit test for hexadecimal digit 

tolower convert character to lowercase 

toupper convert character to uppercase


#### Memory Manipulation Functions

These functions manipulate blocks of memory.  In each case, the address of the memory block and its size is passed to the function.  The functions that begin with "_f" accept far pointers as their arguments allowing manipulation of any memory location regardless of which memory model your program has been compiled for.  The following functions are defined: 

_fmemccpy copy far memory block up to a certain character 

_fmemchr search far memory block for a character value 

_fmemcmp compare any two memory blocks (near or far) 

_fmemcpy copy far memory block, overlap not allowed 

_fmemicmp compare far memory, case insensitive 

_fmemmove copy far memory block, overlap allowed 

_fmemset set any memory block (near of far) to a character 

memccpy copy memory block up to a certain character 

memchr search memory block for a character value 

memcmp compare memory blocks 

memcpy copy memory block, overlap not allowed 

memicmp compare memory, case insensitive 

memmove copy memory block, overlap allowed 

memset set memory block to a character 

movedata copy memory block, with segment information 

swab swap bytes of a memory block 
See the section "String Manipulation Functions" for descriptions of functions that manipulate strings of data.


#### String Manipulation Functions

A string is an array of characters (with type char) that is terminated with an extra null character ('\0').  Functions are passed only the address of the string since the size can be determined by searching for the terminating character.  The functions that begin with "_f" accept far pointers as their arguments allowing manipulation of any memory location regardless of which memory model your program has been compiled for.  The following functions are defined: 

_bprintf formatted transmission to fixed-length string 

_fstrcat concatenate two far strings 

_fstrchr locate character in far string 

_fstrcmp compare two far strings 

_fstrcpy copy far string 

_fstrcspn get number of string characters not from a set of characters 

_fstricmp compare two far strings with case insensitivity 

_fstrlen length of a far string 

_fstrlwr convert far string to lowercase 

_fstrncat concatenate two far strings, up to a maximum length 

_fstrncmp compare two far strings up to maximum length 

_fstrncpy copy a far string, up to a maximum length 

_fstrnicmp compare two far strings with case insensitivity up to a maximum length 

_fstrnset fill far string with character to a maximum length 

_fstrpbrk locate occurrence of a string within a second string 

_fstrrchr locate last occurrence of character from a character set 

_fstrrev reverse a far string in place 

_fstrset fill far string with a character 

_fstrspn find number of characters at start of string which are also in a second string 

_fstrstr find first occurrence of string in second string 

_fstrtok get next token from a far string 

_fstrupr convert far string to uppercase 

sprintf formatted transmission to string 

sscanf scan from string under format control 

strcat concatenate string 

strchr locate character in string 

strcmp compare two strings 

strcmpi compare two strings with case insensitivity 

strcoll compare two strings using locale collating sequence 

strcpy copy a string 

strcspn get number of string characters not from a set of characters 

strdup allocate and duplicate a string 

strerror get error message as string 

stricmp compare two strings with case insensitivity 

strlen string length 

strlwr convert string to lowercase 

strncat concatenate two strings, up to a maximum length 

strncmp compare two strings up to maximum length 

strncpy copy a string, up to a maximum length 

strnicmp compare two strings with case insensitivity up to a maximum length 

strnset fill string with character to a maximum length 

strpbrk locate occurrence of a string within a second string 

strrchr locate last occurrence of character from a character set 

strrev reverse a string in place 

strset fill string with a character 

strspn find number of characters at start of string which are also in a second string 

strstr find first occurrence of string in second string 

strtok get next token from string 

strupr convert string to uppercase 

strxfrm transform string to locale's collating sequence 

_vbprintf same as _bprintf but with variable arguments 

vsprintf same as sprintf but with variable arguments 

vsscanf same as sscanf but with variable arguments 
For related functions see the sections Conversion Functions (conversions to and from strings), Time Functions (formatting of dates and times), and Memory Manipulation Functions (operate on arrays without terminating null character).


#### Multibyte Character Functions

These ANSI C functions provide capabilities for processing multibyte characters.  The following functions are defined: 

mblen determine length of next multibyte character 

mbstowcs convert multibyte character string to wide character string 

mbtowc convert multibyte character to wide character 

wcstombs convert wide character string to multibyte character string 

wctomb convert wide character to multibyte character


#### Conversion Functions

These functions perform conversions between objects of various types and strings.  The following functions are defined: 

atof string to double 

atoi string to int 

atol string to long int 

ecvt double to E-format string 

fcvt double to F-format string 

gcvt double to string 

itoa int to string 

ltoa long int to string 

strtod string to double 

strtol string to long int 

strtoul string to unsigned long int 

ultoa unsigned long int to string 

utoa unsigned int to string 
See also  tolower,  toupper,  strlwr, and  strupr which convert the cases of characters and strings.


#### Memory Allocation Functions

These functions allocate and de-allocate blocks of memory. 
Unless you are running your program in 32-bit protect mode, where segments have a limit of 4 gigabytes, the default data segment has a maximum size of 64K bytes.  It may be less in a machine with insufficient memory or when other programs in the computer already occupy some of the memory.  The  _nmalloc function allocates space within this area while the  _fmalloc function allocates space outside the area (if it is available). 
In a small data model, the  malloc,  calloc and  realloc functions use the  _nmalloc function to acquire memory; in a large data model, the  _fmalloc function is used. 
It is also possible to allocate memory from a based heap using  _bmalloc.  Based heaps are similar to far heaps in that they are located outside the normal data segment.  Based pointers only store the offset portion of the full address, so they behave much like near pointers.  The selector portion of the full address specifies which based heap a based pointer belongs to, and must be passed to the various based heap functions. 
It is important to use the appropriate memory-deallocation function to free memory blocks.  The  _nfree function should be used to free space acquired by the  _ncalloc,  _nmalloc, or  _nrealloc functions; the  _ffree function should be used to free space acquired by the  _fcalloc,  _fmalloc, or  _frealloc functions.  The  _bfree function should be used to free space acquired by the  _bcalloc,  _bmalloc, or  _brealloc functions.  The  free function will use the  _nfree function when the small data memory model is used; it will use the  _ffree function when the large data memory model is being used. 
It should be noted that the  _fmalloc and  _nmalloc functions can both be used in either data memory model.  The following functions are defined: 

alloca allocate auto storage from stack 

_bcalloc allocate and zero memory from a based heap 

_bexpand expand a block of memory in a based heap 

_bfree free a block of memory in a based heap 

_bfreeseg free a based heap 

_bheapseg allocate a based heap 

_bmalloc allocate a memory block from a based heap 

_bmsize return the size of a memory block 

_brealloc re-allocate a memory block in a based heap 

calloc allocate and zero memory 

_expand expand a block of memory 

_fcalloc allocate and zero a memory block (outside default data segment) 

_fexpand expand a block of memory (outside default data segment) 

_ffree free a block allocated using _fmalloc 

_fmalloc allocate a memory block (outside default data segment) 

_fmsize return the size of a memory block 

_frealloc re-allocate a memory block (outside default data segment) 

free free a block allocated using malloc", "calloc or realloc 

_freect return number of objects that can be allocated 

halloc allocate huge array 

hfree free huge array 

malloc allocate a memory block (using current memory model) 

_memavl return amount of available memory 

_memmax return largest block of memory available 

_msize return the size of a memory block 

_ncalloc allocate and zero a memory block (inside default data segment) 

_nexpand expand a block of memory (inside default data segment) 

_nfree free a block allocated using _nmalloc 

_nmalloc allocate a memory block (inside default data segment) 

_nmsize return the size of a memory block 

_nrealloc re-allocate a memory block (inside default data segment) 

realloc re-allocate a block of memory 

sbrk set allocation break position 

stackavail determine available amount of stack space


#### Heap Functions

These functions provide the ability to shrink and grow the heap, as well as, find heap related problems.  The following functions are defined: 

_heapchk perform consistency check on the heap 

_bheapchk perform consistency check on a based heap 

_fheapchk perform consistency check on the far heap 

_nheapchk perform consistency check on the near heap 

_heapgrow grow the heap 

_fheapgrow grow the far heap 

_nheapgrow grow the near heap up to its limit of 64K 

_heapmin shrink the heap as small as possible 

_bheapmin shrink a based heap as small as possible 

_fheapmin shrink the far heap as small as possible 

_nheapmin shrink the near heap as small as possible 

_heapset fill unallocated sections of heap with pattern 

_bheapset fill unallocated sections of based heap with pattern 

_fheapset fill unallocated sections of far heap with pattern 

_nheapset fill unallocated sections of near heap with pattern 

_heapshrink shrink the heap as small as possible 

_fheapshrink shrink the far heap as small as possible 

_bheapshrink shrink a based heap as small as possible 

_nheapshrink shrink the near heap as small as possible 

_heapwalk walk through each entry in the heap 

_bheapwalk walk through each entry in a based heap 

_fheapwalk walk through each entry in the far heap 

_nheapwalk walk through each entry in the near heap


#### Math Functions

These functions operate with objects of type double, also known as floating-point numbers.  The Intel 8087 processor (and its successor chips) is commonly used to implement floating-point operations on personal computers.  Functions ending in "87" pertain to this specific hardware and should be isolated in programs when portability is a consideration.  The following functions are defined: 

abs absolute value of an object of type int 

acos arccosine 

acosh inverse hyperbolic cosine 

asin arcsine 

asinh inverse hyperbolic sine 

atan arctangent of one argument 

atan2 arctangent of two arguments 

atanh inverse hyperbolic tangent 

bessel bessel functions j0, j1, jn, y0, y1, and yn 

cabs absolute value of complex number 

ceil ceiling function 

_clear87 clears floating-point status 

_control87 sets new floating-point control word 

cos cosine 

cosh hyperbolic cosine 

div compute quotient, remainder from division of an int object 

exp exponential function 

fabs absolute value of double 

floor floor function 

fmod modulus function 

_fpreset initializes for floating-point operations 

frexp fractional exponent 

hypot compute hypotenuse 

j0 return Bessel functions of the first kind (described under "bessel Functions") 

j1 return Bessel functions of the first kind (described under "bessel Functions") 

jn return Bessel functions of the first kind (described under "bessel Functions") 

labs absolute value of an object of type long int 

ldexp multiply by a power of two 

ldiv get quotient, remainder from division of object of type long int 

log natural logarithm 

log10 logarithm, base 10 

log2 logarithm, base 2 

matherr handles error from math functions 

max return maximum of two arguments 

min return minimum of two arguments 

modf get integral, fractional parts of double 

pow raise to power 

rand random integer 

sin sine 

sinh hyperbolic sine 

sqrt square root 

srand set starting point for generation of random numbers using rand function 

_status87 gets floating-point status 

tan tangent 

tanh hyperbolic tangent 

y0 return Bessel functions of the second kind (described under "bessel") 

y1 return Bessel functions of the second kind (described under "bessel") 

yn return Bessel functions of the second kind (described under "bessel")


#### Searching Functions

These functions provide searching and sorting capabilities.  The following functions are defined: 

bsearch find a data item in an array using binary search 

lfind find a data item in an array using linear search 

lsearch linear search array, add item if not found 

qsort sort an array


#### Time Functions

These functions are concerned with dates and times.  The following functions are defined: 

_asctime makes time string from time structure 

asctime makes time string from time structure 

clock gets time since program start 

_ctime gets calendar time string 

ctime gets calendar time string 

difftime calculate difference between two times 

ftime returns the current time in a timeb structure 

_gmtime convert calendar time to Coordinated Universal Time (UTC) 

gmtime convert calendar time to Coordinated Universal Time (UTC) 

_localtime convert calendar time to local time 

localtime convert calendar time to local time 

mktime make calendar time from local time 

strftime format date and time 

time get current calendar time 

tzset set global variables to reflect the local time zone


#### Variable-length Argument Lists

Variable-length argument lists are used when a function does not have a fixed number of arguments.  These macros provide the capability to access these arguments.  The following functions are defined: 

va_arg get next variable argument 

va_end complete access of variable arguments 

va_start start access of variable arguments


#### Stream I/O Functions

A stream is the name given to a file or device which has been opened for data transmission.  When a stream is opened, a pointer to a  FILE structure is returned.  This pointer is used to reference the stream when other functions are subsequently invoked. 
There are two modes by which data can be transmitted: 

binary Data is transmitted unchanged. 

text On input, carriage-return characters are removed before following linefeed characters.  On output, carriage-return characters are inserted before linefeed characters. 
These modes are required since text files are stored with the two characters delimiting a line of text, while the C convention is for only the linefeed character to delimit a text line. 
When a program begins execution, there are a number of streams already open for use: 

stdin Standard Input:  input from the console 

stdout Standard Output:  output to the console 

stderr Standard Error:  output to the console (used for error messages) 

stdaux Standard Auxiliary:  auxiliary port, available for use by a program 

stdprn Standard Printer:  available for use by a program 
These standard streams may be re-directed by use of the  freopen function. 
See also the section File Manipulation Functions for other functions which operate upon files. 
The functions referenced in the section Operating System I/O Functions may also be invoked (use the  fileno function to obtain the file handle).  Since the stream functions may buffer input and output, these functions should be used with caution to avoid unexpected results. 
The following functions are defined: 

clearerr clear end-of-file and error indicators for stream 

fclose close stream 

fcloseall close all open streams 

fdopen open stream, given handle 

feof test for end of file 

ferror test for file error 

fflush flush output buffer 

fgetc get next character from file 

fgetchar equivalent to fgetc with the argument stdin 

fgetpos get current file position 

fgets get a string 

flushall flush output buffers for all streams 

fopen open a stream 

fprintf format output 

fputc write a character 

fputchar write a character to the stdout stream 

fputs write a string 

fread read a number of objects 

freopen re-opens a stream 

fscanf scan input according to format 

fseek set current file position, relative 

fsetpos set current file position, absolute 

_fsopen open a shared stream 

ftell get current file position 

fwrite write a number of objects 

getc read character 

getchar get next character from stdin 

gets get string from stdin 

perror write error message to stderr stream 

printf format output to stdout 

putc write character to file 

putchar write character to stdout 

puts write string to stdout 

rewind position to start of file 

scanf scan input from stdin under format control 

setbuf set buffer 

setvbuf set buffering 

tmpfile create temporary file 

ungetc push character back on input stream 

vfprintf same as fprintf but with variable arguments 

vfscanf same as fscanf but with variable arguments 

vprintf same as printf but with variable arguments 

vscanf same as scanf but with variable arguments 
See the section Directory Functions for functions which are related to directories.


#### Process Primitive Functions

These functions deal with process creation, execution and termination, signal handling, and timer operations. 
When a new process is started, it may replace the existing process 

o P_OVERLAY is specified with the  spawn...  functions 
othe  exec...  routines are invoked 
or the existing process may be suspended while the new process executes (control continues at the point following the place where the new process was started) 

o P_WAIT is specified with the  spawn...  functions 
o system is used 
The following functions are defined: 

abort immediate termination of process, return code 3 

atexit register exit routine 

_beginthread start a new thread of execution 

cwait wait for a child process to terminate 

delay delay for number of milliseconds 

_endthread end the current thread 

execl chain to program 

execle chain to program, pass environment 

execlp chain to program 

execlpe chain to program, pass environment 

execv chain to program 

execve chain to program, pass environment 

execvp chain to program 

execvpe chain to program, pass environment 

exit exit process, set return code 

_exit exit process, set return code 

onexit register exit routine 

raise signal an exceptional condition 

signal set handling for exceptional condition 

sleep delay for number of seconds 

spawnl create process 

spawnle create process, set environment 

spawnlp create process 

spawnlpe create process, set environment 

spawnv create process 

spawnve create process, set environment 

spawnvp create process 

spawnvpe create process, set environment 

system execute system command 

wait wait for any child process to terminate 
There are eight  spawn...  and  exec...  functions each.  The "..." is one to three letters: 

o"l" or "v" (one is required) to indicate the way the process parameters are passed 
o"p" (optional) to indicate whether the PATH environment variable is searched to locate the program for the process 
o"e" (optional) to indicate that the environment variables are being passed


#### Process Environment

These functions deal with process identification, process groups, system identification, system time, environment variables, and terminal identification.  The following functions are defined: 

_bgetcmd get command line 

clearenv delete environment variables 

getcmd get command line 

getpid return process ID of calling process 

getenv get environment variable value 

isatty determine if file descriptor associated with a terminal 

putenv add, change or delete environment variable 

_searchenv search for a file in list of directories 

setenv add, change or delete environment variable


#### Directory Functions

These functions pertain to directory manipulation.  The following functions are defined: 

chdir change current working directory 

closedir close opened directory file 

getcwd get current working directory 

mkdir make a new directory 

opendir open directory file 

readdir read file name from directory 

rmdir remove a directory


#### Operating System I/O Functions

These functions operate at the operating-system level and are included for compatibility with other C implementations.  It is recommended that the functions used in the section File Manipulation Functions be used for new programs, as these functions are defined portably and are part of the ANSI standard for the C language. 
The functions in this section reference opened files and devices using a file handle which is returned when the file is opened.  The file handle is passed to the other functions. 
The following functions are defined: 

chsize change the size of a file 

close close file 

creat create a file 

dup duplicate file handle, get unused handle number 

dup2 duplicate file handle, supply new handle number 

eof test for end of file 

filelength get file size 

fileno get file handle for stream file 

fstat get file status 

_hdopen get POSIX handle from OS handle 

lock lock a section of a file 

locking lock/unlock a section of a file 

lseek set current file position 

open open a file 

_os_handle get OS handle from POSIX handle 

read read a record 

setmode set file mode 

sopen open a file for shared access 

tell get current file position 

umask set file permission mask 

unlink delete a file 

unlock unlock a section of a file 

write write a record


#### File Manipulation Functions

These functions operate directly with files.  The following functions are defined: 

access test file or directory for mode of access 

chmod change permissions for a file 

remove delete a file 

rename rename a file 

stat get file status 

tmpnam create name for temporary file 

utime set modification time for a file


#### Console I/O Functions

These functions provide the capability to read and write data from the console.  Data is read or written without any special initialization (devices are not opened or closed), since the functions operate at the hardware level. 
The following functions are defined: 

cgets get a string from the console 

cprintf print formatted string to the console 

cputs write a string to the console 

cscanf scan formatted data from the console 

getch get character from console, no echo 

getche get character from console, echo it 

kbhit test if keystroke available 

putch write a character to the console 

ungetch push back next character from console


#### Default Windowing Functions

These functions provide the capability to manipulate attributes of various windows created by WATCOM's default windowing system for Microsoft Windows 3.x and NT and IBM OS/2. 
The following functions are defined: 

_dwDeleteOnClose delete console window upon close 

_dwSetAboutDlg set about dialogue box title and contents 

_dwSetAppTitle set main window's application title 

_dwSetConTitle set console window's title 

_dwShutDown shut down default windowing system 

_dwYield yield control to other processes


#### BIOS Functions

This set of functions allows access to services provided by the BIOS.  The following functions are defined: 

_bios_disk provide disk access functions 

_bios_equiplist determine equipment list 

_bios_keybrd provide low-level keyboard access 

_bios_memsize determine amount of system board memory 

_bios_printer provide access to printer services 

_bios_serialcom provide access to serial services 

_bios_timeofday get and set system clock


#### DOS-Specific Functions

These functions provide the capability to invoke DOS functions directly from a program.  The following functions are defined: 

bdos DOS call (short form) 

dosexterr extract DOS error information 

_dos_allocmem allocate a block of memory 

_dos_close close a file 

_dos_commit flush buffers to disk 

_dos_creat create a file 

_dos_creatnew create a new file 

_dos_findclose close find file matching 

_dos_findfirst find first file matching a specified pattern 

_dos_findnext find the next file matching a specified pattern 

_dos_freemem free a block of memory 

_dos_getdate get current system date 

_dos_getdiskfree get information about disk 

_dos_getdrive get the current drive 

_dos_getfileattr get file attributes 

_dos_getftime get file's last modification time 

_dos_gettime get the current system time 

_dos_getvect get contents of interrupt vector 

_dos_keep install a terminate-and-stay-resident program 

_dos_open open a file 

_dos_read read data from a file 

_dos_setblock change the size of allocated block 

_dos_setdate change current system date 

_dos_setdrive change the current default drive 

_dos_setfileattr set the attributes of a file 

_dos_setftime set a file's last modification time 

_dos_settime set the current system time 

_dos_setvect set an interrupt vector 

_dos_write write data to a file 

intdos cause DOS interrupt 

intdosx cause DOS interrupt, with segment registers


#### Intel 80x86 Architecture-Specific Functions

These functions provide the capability to invoke Intel 80x86 processor-related functions directly from a program.  Functions that apply to the Intel 8086 CPU apply to that family including the 80286, 80386 and 80486 processors.  The following functions are defined: 

_chain_intr chain to the previous interrupt handler 

_disable disable interrupts 

_enable enable interrupts 

FP_OFF get offset part of far pointer 

FP_SEG get segment part of far pointer 

inp get one byte from hardware port 

inpw get two bytes (one word) from hardware port 

int386 cause 386/486 CPU interrupt 

int386x cause 386/486 CPU interrupt, with segment registers 

int86 cause 8086 CPU interrupt 

int86x cause 8086 CPU interrupt, with segment registers 

intr cause 8086 CPU interrupt, with segment registers 

MK_FP make a far pointer from the segment and offset values 

nosound turn off the speaker 

outp write one byte to hardware port 

outpw write two bytes (one word) to hardware port 

segread read segment registers 

sound turn on the speaker at specified frequency


#### Miscellaneous Functions

The following functions are defined: 

assert test an assertion 

_fullpath return full path specification for file 

_harderr critical error handler 

_hardresume critical error handler resume 

localeconv obtain locale specific conversion information 

longjmp return and restore environment saved by setjmp 

_lrotl rotate an unsigned long left 

_lrotr rotate an unsigned long right 

main the main program (user written) 

offsetof get offset of field in structure 

_rotl rotate an unsigned int left 

_rotr rotate an unsigned int right 

setjmp save environment for use with longjmp function 

_makepath make a full filename from specified components 

setlocale set locale category 

_splitpath split a filename into its components


### Header Files

The following header files are supplied with the C library.  As has been previously noted, when a library function is referenced in a source file, the related header files (shown in the synopsis for that function) should be included into that source file.  The header files provide the proper declarations for the functions and for the number and types of arguments used with them.  Constant values used in conjunction with the functions are also declared.  The files can be included in any order.


#### Header Files in /watcom/h

The following header files are provided with the software.  The header files that are located in the \WATCOM\H directory are described first. 

assert.h This ANSI header file is required when an  assert macro is used.  These assertions will be ignored when the identifier NDEBUG is defined. 

bios.h This header file contains structure definitions and function prototypes for all of the BIOS related functions. 

conio.h This header file provides the declarations for console and Intel 80x86 port input/output functions. 

ctype.h This ANSI header file provides the declarations for functions which manipulate characters. 

direct.h This header file provides the declarations for functions related to directories and for the type  DIR which describes an entry in a directory. 

dos.h This header file is used with functions that interact with DOS.  It includes the definitions for these functions, symbolic names for the numbers of DOS calls, definitions for the  FP_OFF,  FP_SEG and  MK_FP macros, and for the following structures and unions: 

DOSERROR describes the DOS error information. 

REGS describes the CPU registers for Intel 8086 family. 

SREGS describes the segment registers for the Intel 8086 family. 

REGPACK describes the CPU registers and segment registers for Intel 8086 family. 

INTPACK describes the input parameter to an "interrupt" function. 

env.h This POSIX header file contains prototypes for environment string functions. 

errno.h This ANSI header file provides the  extern declaration for error variable  errno and provides the symbolic names for error codes that can be placed in the error variable. 

fcntl.h This POSIX header file provides the flags used by the  open and  sopen functions.  The function declarations for these are found in the <io.h> header file. 

float.h This ANSI header file contains declarations for constants related to floating-point numbers, declarations for low-level floating-point functions, and the declaration of the floating-point exception codes. 

graph.h This header file contains structure definitions and function prototypes for the WATCOM C Graphics library functions.  

io.h This header file contains the declarations for functions that perform input/output operations at the operating system level.  These functions use file handles to reference files or devices.  The function  fstat is declared in the <sys\stat.h> header file. 

limits.h This ANSI header file contains constant declarations for limits or boundary values for ranges of integers and characters.  

locale.h This ANSI header file contains declarations for the categories (LC...) of locales which can be selected using the  setlocale function which is also declared. 

malloc.h This header file provides declarations for the memory allocation and deallocation functions. 

math.h This ANSI header file contains declarations for the mathematical functions (which operate with floating-point numbers) and for the structures: 

exception describes the exception structure passed to the  matherr function; symbolic constants for the types of exceptions are included 

complex declares a complex number 

process.h This header file contains function declarations for the  spawn...  functions, the  exec...  functions, and the  system function.  The file also contains declarations for the constants  P_WAIT,  P_NOWAIT,  P_NOWAITO, and  P_OVERLAY. 

search.h This header file contains function prototypes for the  lfind and  lsearch functions. 

setjmp.h This ANSI header file provides declarations to be used with the  setjmp and  longjmp functions. 

share.h This header file defines constants for shared access to files using the  sopen function. 

signal.h This ANSI header file contains the declarations related to the  signal and  raise functions. 

stdarg.h This ANSI header file contains the declarations for the macros which handle variable argument lists. 

stddef.h This ANSI header file contains declarations for a few popular constants including NULL (null pointer),  size_t (unsigned size of an object), and  ptrdiff_t (difference between two pointers).  It also contains a declaration for the  offsetof macro. 

stdio.h This ANSI header file relates to "standard" input/output functions.  Files, devices and directories are referenced using pointers to objects of the type  FILE.  The header file contains declarations for these functions and macros, defines the  FILE type and contains various constants related to files. 

stdlib.h This ANSI header file contains declarations for many standard functions excluding those declared in other header files discussed in this section. 

string.h This ANSI header file contains declarations for functions which manipulate strings or blocks of memory. 

time.h This ANSI header file declares the functions related to times and dates and defines the structured type  struct tm. 

varargs.h This UNIX System V header file provides an alternate way of handling variable argument lists.  The equivalent ANSI header file is <stdarg.h>.


#### Header Files in /watcom/h/sys

The following header files are present in the  sys subdirectory.  Their presence in this directory indicates that they are system-dependent header files. 

sys\locking.h This header file contains the manifest constants used by the  locking function. 

sys\stat.h This POSIX header file contains the declarations pertaining to file status, including definitions for the  fstat and  stat functions and for the structure: 

stat describes the information obtained for a directory, file or device 

sys\timeb.h This header file describes the  timeb structure used in conjunction with the  ftime function. 

sys\types.h This POSIX header file contains declarations for the types used by system-level calls to obtain file status or time information.  

sys\utime.h This POSIX header file contains a declaration for the  utime function and for the structured type  utimbuf used by it.


### Global Data

Certain data items are used by the WATCOM C run-time library and may be inspected (or changed in some cases) by a program.  The defined items are: 

_amblksiz Prototype in <stdlib.h>. 
This unsigned int data item contains the increment by which the "break" pointer for memory allocation will be advanced when there is no freed block large enough to satisfy a request to allocate a block of memory.  This value may be changed by a program at any time. 

_argc This int item contains the number of arguments passed to  main. 

_argv This char ** item contains a pointer to a vector containing the actual arguments passed to  main. 

daylight Prototype in <time.h>. 
This unsigned int has a value of one when daylight saving time is supported in this locale and zero otherwise.  Whenever a time function is called, the  tzset function is called to set the value of the variable.  The value will be determined from the value of the TZ environment variable. 

_doserrno Prototype in <stdlib.h>. 
This int item contains the actual error code returned when a DOS function fails. 

environ Prototype in <stdlib.h>. 
This char ** __near data item is a pointer to an array of character pointers to the environment strings. 

errno Prototype in <errno.h>. 
This int item contains the number of the last error that was detected.  The run-time library never resets  errno to 0.  Symbolic names for these errors are found in the <errno.h> header file.  See the descriptions for the  perror and  strerror functions for information about the text which describes these errors. 

fltused_ The C compiler places a reference to the  fltused_ symbol into any module that uses a floating-point library routine or library routine that requires floating-point support (e.g., the use of "%f" in the  printf function). 

_fmode Prototype in <stdlib.h>. 
This data item contains the default type of file (text or binary) translation for a file.  It will contain a value of either 

O_BINARY indicates that data is transmitted to and from streams unchanged. 

O_TEXT indicates that carriage return characters are added before linefeed characters on output operations and are removed on input operations when they precede linefeed characters. 
These values are defined in the <fcntl.h> header file.  The value of  _fmode may be changed by a program to change the default behavior of the  open,  fopen,  creat and  sopen functions. 

__minreal Prototype in <stdlib.h>. 
This data item contains the minimum amount of real memory (below 640K) to reserve when running a 32-bit DOS extended application. 

_osmajor Prototype in <stdlib.h>. 
This unsigned char variable contains the major number for the version of DOS executing on the computer.  If the current version is 3.20, then the value will be 3. 

_osminor Prototype in <stdlib.h>. 
This unsigned char variable contains the minor number for the version of DOS executing on the computer.  If the current version is 3.20, then the value will be 20. 

_osmode Prototype in <stdlib.h>. 
This unsigned char variable contains either the value DOS_MODE which indicates the program is running in real address mode, or it contains the value OS2_MODE which indicates the program is running in protected address mode. 

_psp Prototype in <stdlib.h>. 
This data item contains the segment value for the DOS Program Segment Prefix.  Consult the technical documentation for your DOS system for the process information contained in the Program Segment Prefix. 

_stacksize On 16-bit 80x86 systems, this unsigned int value contains the size of the stack for a TINY memory model program.  Changing the value of this item during the execution of a program will have no effect upon the program, since the value is used when the program starts execution.  To change the size of the stack to be 8K bytes, a statement such as follows can be included with the program. 
    
   unsigned int _stacksize = { 8 * 1024 }; 

stdaux Prototype in <stdio.h>. 
This variable (with type FILE *) indicates the standard auxiliary port. 

stderr Prototype in <stdio.h>. 
This variable (with type FILE *) indicates the standard error stream (set to the console by default). 

stdin Prototype in <stdio.h>. 
This variable (with type FILE *) indicates the standard input stream (set to the console by default). 

stdout Prototype in <stdio.h>. 
This variable (with type FILE *) indicates the standard output stream (set to the console by default). 

stdprn Prototype in <stdio.h>. 
This variable (with type FILE *) indicates the standard printer. 

sys_errlist Prototype in <stdlib.h>. 
This variable is an array of pointers to character strings for each error code defined in the <errno.h> header file. 

sys_nerr Prototype in <stdlib.h>. 
This int variable contains the number of messages declared in  sys_errlist. 

_threadid Prototype in <stddef.h>. 
This variable contains a far pointer to an int which points to the id of the current thread.  This variable is defined only in the CLIBMTL library for OS/2. 

timezone Prototype in <time.h>. 
This long int contains the number of seconds of time that the local time zone is earlier than Coordinated Universal Time (UTC) (formerly known as Greenwich Mean Time (GMT)).  Whenever a time function is called, the  tzset function is called to set the value of the variable.  The value will be determined from the value of the TZ environment variable. 

tzname Prototype in <time.h>. 
This array of two pointers to character strings indicates the name of the standard abbreviation for the time zone and the name of the abbreviation for the time zone when daylight saving time is in effect.  Whenever a time function is called, the  tzset function is called to set the values in the array.  These values will be determined from the value of the TZ environment variable. 

__win_flags_alloc Prototype in <stdlib.h>. 
This unsigned long int variable contains the flags to be used when allocating memory in Windows. 

__win_flags_realloc Prototype in <stdlib.h>. 
This unsigned long int variable contains the flags to be used when reallocating memory in Windows.


### The TZ Environment Variable

The  TZ environment variable is used to establish the local time zone.  The value of the variable is used by various time functions to compute times relative to Coordinated Universal Time (UTC) (formerly known as Greenwich Mean Time (GMT)). 
The time on the computer should be set to the local time.  Use the DOS time command and the DOS date command if the time is not automatically maintained by the computer hardware. 
The  TZ environment variable can be set (before the program is executed) by using the DOS set command as follows: 
    
     SET TZ=PST8PDT 
or (during the program execution) by using the  setenv or  putenv library functions: 
    
     setenv( "TZ", "PST8PDT", 1 ); 
     putenv( "TZ=PST8PDT" ); 
The value of the variable can be obtained by using the  getenv function: 
    
     char *tzvalue; 
     . . . 
     tzvalue = getenv( "TZ" ); 
The  tzset function processes the  TZ environment variable and sets the global variables  daylight (indicates if daylight saving time is supported in the locale),  timezone (contains the number of seconds of time difference between the local time zone and Coordinated Universal Time (UTC)), and  tzname (a vector of two pointers to character strings containing the standard and daylight time-zone names). 
The value of the  TZ environment variable should be set as follows (spaces are for clarity only): 

std offset dst offset , rule 
The expanded format is as follows: 

stdoffset[dst[offset][,start[/time],end[/time]]] 

std, dst three or more letters that are the designation for the standard (std) or summer (dst) time zone.  Only std is required.  If dst is omitted, then summer time does not apply in this locale.  Upper- and lowercase letters are allowed.  Any characters except for a leading colon (:), digits, comma (,), minus (-), plus (+), and ASCII NUL (\0) are allowed. 

offset indicates the value one must add to the local time to arrive at Coordinated Universal Time (UTC).  The offset has the form: 

hh[:mm[:ss]] 
The minutes (mm) and seconds (ss) are optional.  The hour (hh) is required and may be a single digit.  The offset following std is required.  If no offset follows dst, summer time is assumed to be one hour ahead of standard time.  One or more digits may be used; the value is always interpreted as a decimal number.  The hour may be between 0 and 24, and the minutes (and seconds) - if present - between 0 and 59.  If preceded by a "-", the time zone will be east of the  Prime Meridian ; otherwise it will be west (which may be indicated by an optional preceding "+"). 

rule indicates when to change to and back from summer time.  The rule has the form: 

date/time,date/time 
where the first date describes when the change from standard to summer time occurs and the second date describes when the change back happens.  Each time field describes when, in current local time, the change to the other time is made. 
The format of date may be one of the following: 

Jn The Julian day n (1 <= n <= 365).  Leap days are not counted.  That is, in all years - including leap years - February 28 is day 59 and March 1 is day 60.  It is impossible to explicitly refer to the occasional February 29. 

n The zero-based Julian day (0 <= n <= 365).  Leap years are counted, and it is possible to refer to February 29. 

Mm.n.d The d'th day (0 <= d <= 6) of week n of month m of the year (1 <= n <= 5, 1 <= m <= 12, where week 5 means "the last d day in month m" which may occur in the fourth or fifth week).  Week 1 is the first week in which the d'th day occurs.  Day zero is Sunday. 
The time has the same format as offset except that no leading sign ("+" or "-") is allowed.  The default, if time is omitted, is 02:00:00. 
Whenever  ctime,  _ctime,  localtime,  _localtime or  mktime is called, the time zone names contained in the external variable  tzname will be set as if the  tzset function had been called.  The same is true if the %Z directive of  strftime is used. 
Some examples are: 

TZ=EST5EDT Eastern Standard Time is 5 hours earlier than Coordinated Universal Time (UTC).  Standard time and daylight saving time both apply to this locale.  By default, Eastern Daylight Time (EDT) is one hour ahead of standard time (i.e., EDT4).  Since it is not specified, daylight saving time starts on the first Sunday of April at 2:00 A.M.  and ends on the last Sunday of October at 2:00 A.M.  This is the default when the  TZ variable is not set. 

TZ=EST5EDT4,M4.1.0/02:00:00,M10.5.0/02:00:00 This is the full specification for the default when the  TZ variable is not set.  Eastern Standard Time is 5 hours earlier than Coordinated Universal Time (UTC).  Standard time and daylight saving time both apply to this locale.  Eastern Daylight Time (EDT) is one hour ahead of standard time.  Daylight saving time starts on the first (1) Sunday (0) of April (4) at 2:00 A.M.  and ends on the last (5) Sunday (0) of October (10) at 2:00 A.M. 

TZ=PST8PDT Pacific Standard Time is 8 hours earlier than Coordinated Universal Time (UTC).  Standard time and daylight saving time both apply to this locale.  By default, Pacific Daylight Time is one hour ahead of standard time (i.e., PDT7).  Since it is not specified, daylight saving time starts on the first Sunday of April at 2:00 A.M.  and ends on the last Sunday of October at 2:00 A.M. 

TZ=NST3:30NDT1:30 Newfoundland Standard Time is 3 and 1/2 hours earlier than Coordinated Universal Time (UTC).  Standard time and daylight saving time both apply to this locale.  Newfoundland Daylight Time is 1 and 1/2 hours earlier than Coordinated Universal Time (UTC). 

TZ=Central Europe Time-2:00 Central European Time is 2 hours later than Coordinated Universal Time (UTC).  Daylight saving time does not apply in this locale.


## Graphics Library


### Graphics Functions

The WATCOM C Graphics Library consists of a large number of functions.  These functions are used to display graphical images such as lines and circles upon the computer screen.  Functions are also provided for displaying text along with the graphics output.


### Graphics Adapters

Support is provided for both color and monochrome screens which are connected to the computer using any of the following graphics adapters: 

oIBM Monochrome Display/Printer Adapter (MDPA) 
oIBM Color Graphics Adapter (CGA) 
oIBM Enhanced Graphics Adapter (EGA) 
oIBM Multi-Color Graphics Array (MCGA) 
oIBM Video Graphics Array (VGA) 
oHercules Monochrome Adapter 
oSuperVGA adapters (SVGA) supplied by various manufacturers


### Classes of Graphics Functions

The functions in the WATCOM C Graphics Library can be organized into a number of classes: 

Environment Functions 
These functions deal with the hardware environment. 

Coordinate System Functions 
These functions deal with coordinate systems and mapping coordinates from one system to another. 

Attribute Functions 
These functions control the display of graphical images. 

Drawing Functions 
These functions display graphical images such as lines and ellipses. 

Text Functions 
These functions deal with displaying text in both graphics and text modes. 

Graphics Text Functions 
These functions deal with displaying graphics text. 

Image Manipulation Functions 
These functions store and retrieve screen images. 

Font Manipulation Functions 
These functions deal with displaying font based text. 

Presentation Graphics Functions 
These functions deal with displaying presentation graphics elements such as bar charts and pie charts. 
The following subsections describe these function classes in more detail.  Each function in the class is noted with a brief description of its purpose.


#### Environment Functions

These functions deal with the hardware environment.  The  _getvideoconfig function returns information about the current video mode and the hardware configuration.  The  _setvideomode function selects a new video mode. 
Some video modes support multiple pages of screen memory.  The visual page (the one displayed on the screen) may be different than the active page (the one to which objects are being written). 
The following functions are defined: 

_getactivepage get the number of the current active graphics page 

_getvideoconfig get information about the graphics configuration 

_getvisualpage get the number of the current visual graphics page 

_grstatus get the status of the most recently called graphics library function 

_setactivepage set the active graphics page (the page to which graphics objects are drawn) 

_settextrows set the number of rows of text displayed on the screen 

_setvideomode select the video mode to be used 

_setvideomoderows select the video mode and the number of text rows to be used 

_setvisualpage set the visual graphics page (the page displayed on the screen)


#### Coordinate System Functions

These functions deal with coordinate systems and mapping coordinates from one system to another.  The WATCOM C Graphics Library supports three coordinate systems: 

 1.Physical coordinates 

 2.View coordinates 

 3.Window coordinates 
Physical coordinates match the physical dimensions of the screen.  The physical origin, denoted (0,0), is located at the top left corner of the screen.  A pixel to the right of the origin has a positive x-coordinate and a pixel below the origin will have a positive y-coordinate.  The x- and y-coordinates will never be negative values. 
The view coordinate system can be defined upon the physical coordinate system by moving the origin from the top left corner of the screen to any physical coordinate (see the  _setvieworg function).  In the view coordinate system, negative x- and y-coordinates are allowed.  The scale of the view and physical coordinate systems is identical (both are in terms of pixels). 
The window coordinate system is defined in terms of a range of user-specified values (see the  _setwindow function).  These values are scaled to map onto the physical coordinates of the screen.  This allows for consistent pictures regardless of the resolution (number of pixels) of the screen. 
The following functions are defined: 

_getcliprgn get the boundary of the current clipping region 

_getphyscoord get the physical coordinates of a point in view coordinates 

_getviewcoord get the view coordinates of a point in physical coordinates 

_getviewcoord_w get the view coordinates of a point in window coordinates 

_getviewcoord_wxy get the view coordinates of a point in window coordinates 

_getwindowcoord get the window coordinates of a point in view coordinates 

_setcliprgn set the boundary of the clipping region 

_setvieworg set the position to be used as the origin of the view coordinate system 

_setviewport set the boundary of the clipping region and the origin of the view coordinate system 

_setwindow define the boundary of the window coordinate system


#### Attribute Functions

These functions control the display of graphical images such as lines and circles.  Lines and figures are drawn using the current color (see the  _setcolor function), the current line style (see the  _setlinestyle function), the current fill mask (see the  _setfillmask function), and the current plotting action (see the  _setplotaction function). 
The following functions are defined: 

_getarcinfo get the endpoints of the most recently drawn arc 

_getbkcolor get the background color 

_getcolor get the current color 

_getfillmask get the current fill mask 

_getlinestyle get the current line style 

_getplotaction get the current plotting action 

_remapallpalette assign colors for all pixel values 

_remappalette assign color for one pixel value 

_selectpalette select a palette 

_setbkcolor set the background color 

_setcolor set the current color 

_setfillmask set the current fill mask 

_setlinestyle set the current line style 

_setplotaction set the current plotting action


#### Drawing Functions

These functions display graphical images such as lines and ellipses.  Functions exist to draw straight lines (see the  _lineto functions), rectangles (see the  _rectangle functions), polygons (see the  _polygon functions), ellipses (see the  _ellipse functions), elliptical arcs (see the  _arc functions) and pie-shaped wedges from ellipses (see the  _pie functions). 
These figures are drawn using the attributes described in the previous section.  The functions ending with _w or _wxy use the window coordinate system; the others use the view coordinate system. 
The following functions are defined: 

_arc draw an arc 

_arc_w draw an arc using window coordinates 

_arc_wxy draw an arc using window coordinates 

_clearscreen clear the screen and fill with the background color 

_ellipse draw an ellipse 

_ellipse_w draw an ellipse using window coordinates 

_ellipse_wxy draw an ellipse using window coordinates 

_floodfill fill an area of the screen with the current color 

_floodfill_w fill an area of the screen in window coordinates with the current color 

_getcurrentposition get the coordinates of the current output position 

_getcurrentposition_w get the window coordinates of the current output position 

_getpixel get the color of the pixel at the specified position 

_getpixel_w get the color of the pixel at the specified position in window coordinates 

_lineto draw a line from the current position to a specified position 

_lineto_w draw a line from the current position to a specified position in window coordinates 

_moveto set the current output position 

_moveto_w set the current output position using window coordinates 

_pie draw a wedge of a "pie" 

_pie_w draw a wedge of a "pie" using window coordinates 

_pie_wxy draw a wedge of a "pie" using window coordinates 

_polygon draw a polygon 

_polygon_w draw a polygon using window coordinates 

_polygon_wxy draw a polygon using window coordinates 

_rectangle draw a rectangle 

_rectangle_w draw a rectangle using window coordinates 

_rectangle_wxy draw a rectangle using window coordinates 

_setpixel set the color of the pixel at the specified position 

_setpixel_w set the color of the pixel at the specified position in window coordinates


#### Text Functions

These functions deal with displaying text in both graphics and text modes.  This type of text output can be displayed in only one size. 
This text is displayed using the  _outtext and  _outmem functions.  The output position for text follows the last text that was displayed or can be reset (see the  _settextposition function).  Text windows can be created (see the  _settextwindow function) in which the text will scroll.  Text is displayed with the current text color (see the  _settextcolor function). 
The following functions are defined: 

_clearscreen clear the screen and fill with the background color 

_displaycursor determine whether the cursor is to be displayed after a graphics function completes execution 

_getbkcolor get the background color 

_gettextcolor get the color used to display text 

_gettextcursor get the shape of the text cursor 

_gettextposition get the current output position for text 

_gettextwindow get the boundary of the current text window 

_outmem display a text string of a specified length 

_outtext display a text string 

_scrolltextwindow scroll the contents of the text window 

_setbkcolor set the background color 

_settextcolor set the color used to display text 

_settextcursor set the shape of the text cursor 

_settextposition set the output position for text 

_settextwindow set the boundary of the region used to display text 

_wrapon permit or disallow wrap-around of text in a text window


#### Graphics Text Functions

These functions deal with displaying graphics text.  Graphics text is displayed as a sequence of line segments, and can be drawn in different sizes (see the  _setcharsize function), with different orientations (see the  _settextorient function) and alignments (see the  _settextalign function).  The functions ending with _w use the window coordinate system; the others use the view coordinate system. 
The following functions are defined: 

_gettextextent get the bounding rectangle for a graphics text string 

_gettextsettings get information about the current settings used to display graphics text 

_grtext display graphics text 

_grtext_w display graphics text using window coordinates 

_setcharsize set the character size used to display graphics text 

_setcharsize_w set the character size in window coordinates used to display graphics text 

_setcharspacing set the character spacing used to display graphics text 

_setcharspacing_w set the character spacing in window coordinates used to display graphics text 

_settextalign set the alignment used to display graphics text 

_settextorient set the orientation used to display graphics text 

_settextpath set the path used to display graphics text


#### Image Manipulation Functions

These functions are used to transfer screen images.  The  _getimage function transfers a rectangular image from the screen into memory.  The  _putimage function transfers an image from memory back onto the screen.  The functions ending with _w or _wxy use the window coordinate system; the others use the view coordinate system. 
The following functions are defined: 

_getimage store an image of an area of the screen into memory 

_getimage_w store an image of an area of the screen in window coordinates into memory 

_getimage_wxy store an image of an area of the screen in window coordinates into memory 

_imagesize get the size of a screen area 

_imagesize_w get the size of a screen area in window coordinates 

_imagesize_wxy get the size of a screen area in window coordinates 

_putimage display an image from memory on the screen 

_putimage_w display an image from memory on the screen using window coordinates


#### Font Manipulation Functions

These functions are for the display of fonts compatible with Microsoft Windows.  Fonts are contained in files with an extension of .FON.  Before font based text can be displayed, the fonts must be registered with the  _registerfonts function, and a font must be selected with the  _setfont function. 
The following functions are defined: 

_getfontinfo get information about the currently selected font 

_getgtextextent get the length in pixels of a text string 

_getgtextvector get the current value of the font text orientation vector 

_outgtext display a string of text in the current font 

_registerfonts initialize the font graphics system 

_setfont select a font from among the registered fonts 

_setgtextvector set the font text orientation vector 

_unregisterfonts frees memory allocated by the font graphics system


#### Presentation Graphics Functions

These functions provide a system for displaying and manipulating presentation graphics elements such as bar charts and pie charts.  The presentation graphics functions can be further divided into three classes: 

Display Functions 
These functions are for the initialization of the presentation graphics system and the displaying of charts. 

Analyze Functions 
These functions calculate default values for chart elements without actually displaying the chart. 

Utility Functions 
These functions provide additional support to control the appearance of presentation graphics elements. 
The following subsections describe these function classes in more detail.  Each function in the class is noted with a brief description of its purpose.


##### Display Functions

These functions are for the initialization of the presentation graphics system and the displaying of charts.  The  _pg_initchart function initializes the system and should be the first presentation graphics function called.  The single-series functions display a single set of data on a chart; the multi-series functions (those ending with ms) display several sets of data on the same chart. 
The following functions are defined: 

_pg_chart display a bar, column or line chart 

_pg_chartms display a multi-series bar, column or line chart 

_pg_chartpie display a pie chart 

_pg_chartscatter display a scatter chart 

_pg_chartscatterms display a multi-series scatter chart 

_pg_defaultchart initialize the chart environment for a specific chart type 

_pg_initchart initialize the presentation graphics system


##### Analyze Functions

These functions calculate default values for chart elements without actually displaying the chart.  The functions ending with ms analyze multi-series charts; the others analyze single-series charts. 
The following functions are defined: 

_pg_analyzechart analyze a bar, column or line chart 

_pg_analyzechartms analyze a multi-series bar, column or line chart 

_pg_analyzepie analyze a pie chart 

_pg_analyzescatter analyze a scatter chart 

_pg_analyzescatterms analyze a multi-series scatter chart


##### Utility Functions

These functions provide additional support to control the appearance of presentation graphics elements. 
The following functions are defined: 

_pg_getchardef get bit-map definition for a specific character 

_pg_getpalette get presentation graphics palette (colors, line styles, fill patterns and plot characters) 

_pg_getstyleset get presentation graphics style-set (line styles for window borders and grid lines) 

_pg_hlabelchart display text horizontally on a chart 

_pg_resetpalette reset presentation graphics palette to default values 

_pg_resetstyleset reset presentation graphics style-set to default values 

_pg_setchardef set bit-map definition for a specific character 

_pg_setpalette set presentation graphics palette (colors, line styles, fill patterns and plot characters) 

_pg_setstyleset set presentation graphics style-set (line styles for window borders and grid lines) 

_pg_vlabelchart display text vertically on a chart


### Graphics Header Files

All program modules which use the Graphics Library should include the header file graph.h.  This file contains prototypes for all the functions in the library as well as the structures and constants used by them. 
Modules using the presentation graphics functions should also include the header file pgchart.h.


## DOS Considerations

For the most part, DOS (Disk Operating System) for your personal computer can be ignored, unless an application is highly dependent upon the hardware or uses specialized functions from the operating system.  In this section, some of these aspects will be addressed.  For a more detailed explanation, the technical documentation for the DOS that you are using should be consulted.


### DOS Devices

Most of the hardware devices attached to your computer have names which are recognized by DOS.  These names cannot be used as the names of files.  Some examples are: 

CON the console (screen) 

AUX the serial (auxiliary) port 

COM1 serial port 1 

COM2 serial port 2 

PRN the printer on the parallel port 

LPT1 the printer on the first parallel port 

LPT2 the printer on the second parallel port 

LPT3 the printer on the third parallel port 

NUL a non-existent device, which accepts (and discards) output 
Disks (such as diskette drives and hard disks) are specified as single letters, starting with the letter A.  A colon character (:) follows the letter for the drive.  Either uppercase or lowercase letters can be used.  Some examples are: 

A: the first disk drive 

a: the first disk drive 

e: the fifth disk drive


### DOS Directories

Each disk drive is conceptually divided into directories.  Each directory is capable of containing files and/or other directories.  The initial directory, called the root directory, is not named; all other directories are named and can be accessed with a path specification.  A path is either absolute or relative to the current working directory.  Some examples are: 

b:\ the root directory of the second disk drive 

\ the root directory of the current disk drive 

\outer\middle\inner 
directory inner which is contained within directory middle which is contained within directory outer which is contained within the root directory of the current disk drive. 
Directory names are separated by backslash characters (\).  The initial backslash character informs DOS that the path starts with the root directory.  When the first character is not a backslash, the path starts with the current working directory on the indicated device. 
The DOS CHDIR (CD) command can be used to change the current working directory for a device.  Suppose that the following DOS commands were issued: 
    
   chdir a:\apps\payroll 
   chdir c:\mydir 
Then, the following path specifications are: 

a:xxx\y a:\apps\payroll\xxx\y 

c:zzzzz c:\mydir\zzzzz 
When no drive is specified, DOS uses the current disk drive.


### DOS File Names

The name of a file within a directory has the format filename.ext where the required filename portion is up to eight characters in length and the optional ext portion is up to three characters in length.  A period character (.) separates the two names when the ext portion is present. 
More than eight characters can be given in the filename.  DOS truncates the name to eight characters when a longer filename is given.  This may lead to erroneous results in some cases, since the files MYBIGDATAFILE and MYBIGDATES both refer to the file MYBIGDAT. 
The characters used in file names may be letters, digits as well as some other characters documented in your DOS technical documentation.  Most people restrict their file names to contain only letters and digits.  Uppercase and lowercase letters are treated as being equivalent (file names are case insensitive).  Thus, the files 
    
   MYDATA.NEW 
   mydata.new 
   MyData.New 
all refer to the same file. 
You cannot use a DOS device name (such as  CON or  PRN, for example) for a file name.  See the section DOS Devices for a list of these reserved names. 
A complete file designation has the following format: 
    
   drive:\path\filename.ext 
where: 

drive: is an optional disk drive specification.  If omitted, the default drive is used.  Some examples are: 
    
   A:  (first disk drive) 
   c:  (third disk drive) 

\path\ is the path specification for the directory containing the desired file.  Some examples are: 
    
   \mylib\ 
   \apps\payroll\ 

filename.ext is the name of the file. 
Suppose that the current working directories are as follows: 

A: \payroll 

B: \      (root directory) 

C: \source\c 
and that the default disk drive is C:.  Then, the following file designations will result in the indicated file references: 

pgm.c C:\SOURCE\C\PGM.C 

\basic.dat C:\BASIC.DAT 

paypgm\outsep.c C:\SOURCE\C\PAYPGM\OUTSEP.C 

b:data B:\DATA 

a:employee A:\PAYROLL\EMPLOYEE 

a:\deduct\yr1988 A:\DEDUCT\YR1988


### DOS Files

DOS files are stored within directories on disk drives.  Most software, including WATCOM C, treats files in two representations: 

BINARY These files can contain arbitrary data.  It is the responsibility of the software to recognize records within the file if they exist. 

TEXT These files contain lines of "printable" characters.  Each line is delimited by a carriage return character followed by a linefeed character. 
Since the conceptual view of text files in the C language is that lines are terminated by only linefeed characters, the C library will remove carriage returns on input and add them on output, provided the mode is set to be text.  This mode is set upon opening the file or with the  setmode function.


### DOS Commands

DOS commands are documented in the technical documentation for your DOS system.  These may be invoked from a C program with the  system function.


### DOS Interrupts

DOS interrupts and 8086 interrupts are documented in the technical documentation for your DOS system.  These may be generated from a C program by calling the  bdos,  intdos,  intdosx,  intr,  int386,  int386x,  int86 and  int86x functions.


### DOS Processes

Currently, DOS has the capability to execute only one process at a time.  Thus, when a process is initiated with the  spawn...  parameter  P_WAIT, the new process will execute to completion before control returns to the initiating program.  Otherwise, the new task replaces the initial task.  Tasks can be started by using the  system,  exec...  and  spawn...  functions.


## Library Functions and Macros

Each of the functions or macros in the C Library is described in this chapter.  Each description consists of a number of subsections: 

Synopsis: This subsection gives the header files that should be included within a source file that references the function or macro.  It also shows an appropriate declaration for the function or for a function that could be substituted for a macro. This declaration is not included in your program; only the header file(s) should be included. 
When a pointer argument is passed to a function and that function does not modify the item indicated by that pointer, the argument is shown with  const before the argument.  For example, 
    
   const char *string 
indicates that the array pointed at by string is not changed. 

Description: This subsection is a description of the function or macro. 

Returns: This subsection describes the return value (if any) for the function or macro. 

Errors: This subsection describes the possible  errno values. 

See Also: This optional subsection provides a list of related functions or macros. 

Example: This optional subsection consists of one or more examples of the use of the function.  The examples are often just fragments of code (not complete programs) for illustration purposes. 

Classification: This subsection provides an indication of where the function or macro is commonly found.  The following notation is used: 

ANSI These functions or macros are defined by the ANSI C standard. 

POSIX 1003.1 These functions or macros are not defined by the ANSI C standard.  These function are specified in the document IEEE Standard Portable Operating System Interface for Computer Environments (IEEE Draft Standard 1003.1-1990). 

BIOS These functions access a service of the BIOS found in IBM Personal Computers and compatibles.  These functions should not be used if portability is a consideration. 

DOS These functions or macros are neither ANSI nor POSIX.  They perform a function related to DOS.  They may be found in other implementations of C for personal computers with DOS.  Use these functions with caution, if portability is a consideration. 

Intel These functions or macros are neither ANSI nor POSIX.  They performs a function related to the Intel x86 architecture.  They may be found in other implementations of C for personal computers using Intel chips.  Use these functions with caution, if portability is a consideration. 

OS/2 These functions are specific to OS/2. 

PC Graphics These functions are part of the PC graphics library. 

Windows These functions are specific to Microsoft Windows. 

WATCOM These functions or macros are neither ANSI nor POSIX.  They may be found in other implementations of the C language, but caution should be used if portability is a consideration. 

Systems: This subsection provides an indication of where the function or macro is supported.  The following notation is used: 

All This function is available on all systems. 

DOS This function is available on both 16-bit DOS and 32-bit extended DOS. 

DOS/16 This function is available on 16-bit, real-mode DOS. 

DOS/32 This function is available on 32-bit, protect-mode extended DOS. 

DOS/PM This 16-bit DOS protect-mode function is supported under Phar Lap's 286|DOS-Extender "RUN286".  The function is found in one of WATCOM's 16-bit protect-mode DOS libraries (DOSPM*.LIB under the 16-bit OS2 subdirectory). 

MACRO This function is implemented as a macro (#define) under all systems. 

NT This function is available on Microsoft Windows NT, a 32-bit protect-mode system for Intel 80386 and upwards compatible systems. 

OS/2 1.x This function is available on IBM OS/2 1.x, a 16-bit protect-mode system for Intel 80286 and upwards compatible systems. 
When "(MT)" appears after OS/2, it refers to the CLIBMTL library which supports multi-threaded applications. 
When "(DL)" appears after OS/2, it refers to the CLIBDLL library which supports creation of Dynamic Link Libraries. 
When "(all)" appears after "OS/2 1", it means all versions of the OS/2 1.x libraries. 
If a function is missing from the OS/2 library, it may be found in WATCOM's 16-bit protect-mode DOS libraries (DOSPM*.LIB) for Phar Lap's 286|DOS-Extender (RUN286). 

OS/2 2.x This function is available on IBM OS/2 2.x, a 32-bit protect-mode system for Intel 80386 and upwards compatible systems. 

QNX This function is available on QNX Software Systems' 16 or 32-bit operating systems. 

QNX/16 This function is available on QNX Software Systems' 16-bit operating system. 

QNX/32 This function is available on QNX Software Systems' 32-bit operating system. 

Win This function is available on 16-bit, protect-mode Microsoft Windows 3.x and Windows 3.x extended for 32-bit protect-mode applications running on Intel 386 or upward compatible systems.  This latter support is provided by WATCOM C/386. 

Win/16 This function is available on 16-bit, protect-mode Windows 3.x. 

Win/32 This function is available on Microsoft Windows 3.x, extended for 32-bit protect-mode applications running on Intel 386 or upward compatible systems.  This support is provided by WATCOM C/386.


### abort

Synopsis: 
#include <stdlib.h> 
void abort( void ); 

Description: The abort function raises the signal SIGABRT.  The default action for SIGABRT is to terminate program execution, returning control to the process that started the calling program (usually the operating system).  The status unsuccessful termination is returned to the invoking process by means of the function call raise(SIGABRT).  Under DOS and OS/2, the status value is 3. 

Returns: The abort function does not return to its caller. 

See Also: atexit, _bgetcmd, exec Functions, exit, _exit, getcmd, getenv, main, onexit, putenv, spawn Functions, system 

Example: 
#include <stdlib.h> 
void main() 
 { 
  int major_error = 1; 
  if( major_error ) 
   abort(); 
 } 

Classification: ANSI 

Systems: All


### abs

Synopsis: 
#include <stdlib.h> 
int abs( int j ); 

Description: The abs function returns the absolute value of its integer argument j. 

Returns: The abs function returns the absolute value of its argument. 

See Also: fabs, labs 

Example: 
#include <stdio.h> 
#include <stdlib.h> 
void main() 
 { 
  printf( "%d %d %d\n", abs( -5 ), abs( 0 ), abs( 5 ) ); 
 } 
produces the following: 
5 0 5 

Classification: ANSI 

Systems: All


### access

Synopsis: 
#include <io.h> 
int access( const char *path, int mode ); 

Description: The access function determines if the file or directory specified by path exists and if it can be accessed with the file permission given by mode. 
When the value of mode is zero, only the existence of the file is verified.  The read and/or write permission for the file can be determined when mode is a combination of the bits: 

R_OK test for read permission 

W_OK test for write permission 

X_OK test for execute permission 

F_OK test for existence of file 
With DOS, all files have read permission; it is a good idea to test for read permission anyway, since a later version of DOS may support write-only files. 

Returns: The access returns zero if the file or directory exists and can be accessed with the specified mode.  Otherwise, -1 is returned and  errno is set to indicate the error. 

Errors: When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

EACCES Access denied because the file's permission does not allow the specified access. 

ENOENT Path or file not found. 

See Also: chmod, fstat, open, sopen, stat 

Example: 
#include <stdio.h> 
#include <stdlib.h> 
#include <io.h> 
void main( int argc, char *argv[] ) 
 { 
  if( argc != 2 ) { 
   fprintf( stderr, "Use: check <filename>\n" ); 
   exit( 1 ); 
  } 
  if( access( argv[1], F_OK ) == 0 ) { 
   printf( "%s exists\n", argv[1] ); 
  } else { 
   printf( "%s does not exist\n", argv[1] ); 
   exit( EXIT_FAILURE ); 
  } 
  if( access( argv[1], R_OK ) == 0 ) { 
   printf( "%s is readable\n", argv[1] ); 
  } 
  if( access( argv[1], W_OK ) == 0 ) { 
   printf( "%s is writeable\n", argv[1] ); 
  } 
  if( access( argv[1], X_OK ) == 0 ) { 
   printf( "%s is executable\n", argv[1] ); 
  } 
  exit( EXIT_SUCCESS ); 
 } 

Classification: POSIX 1003.1 

Systems: All


### acos

Synopsis: 
#include <math.h> 
double acos( double x ); 

Description: The acos function computes the principal value of the arccosine of x.  A domain error occurs for arguments not in the range [-1,1]. 

Returns: The acos function returns the arccosine in the range [0,P].  When the argument is outside the permissible range, the  matherr function is called.  Unless the default  matherr function is replaced, it will set the global variable  errno to  EDOM, and print a "DOMAIN error" diagnostic message using the  stderr stream. 

See Also: asin, atan, atan2, matherr 

Example: 
#include <stdio.h> 
#include <math.h> 
void main() 
 { 
  printf( "%f\n", acos(.5) ); 
 } 
produces the following: 
1.047197 

Classification: ANSI 

Systems: All


### acosh

Synopsis: 
#include <math.h> 
double acosh( double x ); 

Description: The acosh function computes the inverse hyperbolic cosine of x.  A domain error occurs if the value of x is less than 1.0. 

Returns: The acosh function returns the inverse hyperbolic cosine value.  When the argument is outside the permissible range, the  matherr function is called.  Unless the default  matherr function is replaced, it will set the global variable  errno to  EDOM, and print a "DOMAIN error" diagnostic message using the  stderr stream. 

See Also: asinh, atanh, cosh, matherr 

Example: 
#include <stdio.h> 
#include <math.h> 
void main() 
 { 
  printf( "%f\n", acosh( 1.5 ) ); 
 } 
produces the following: 
0.962424 

Classification: WATCOM 

Systems: All


### alloca

Synopsis: 
#include <malloc.h> 
void *alloca( size_t size ); 

Description: The alloca function allocates space for an object of size bytes from the stack.  The allocated space is automatically discarded when the current function exits.  The alloca function should not be used in an expression that is an argument to a function. 

Returns: The alloca function returns a pointer to the start of the allocated memory.  The return value is NULL if there is insufficient stack space available. 

See Also: calloc, malloc, stackavail 

Example: 
#include <stdio.h> 
#include <string.h> 
#include <malloc.h> 
FILE *open_err_file( char * ); 
void main() 
 { 
  FILE *fp; 
  fp = open_err_file( "alloca" ); 
  if( fp == NULL ) { 
   printf( "Unable to open error file\n" ); 
  } else { 
   fclose( fp ); 
  } 
 } 
FILE *open_err_file( char *name ) 
 { 
   char *buffer; 
   /* allocate temp buffer for file name */ 
   buffer = (char *) alloca( strlen(name) + 5 ); 
   if( buffer ) { 
    sprintf( buffer, "%s.err", name ); 
    return( fopen( buffer, "w" ) ); 
   } 
   return( (FILE *) NULL ); 
 } 

Classification: WATCOM 

Systems: MACRO


### _arc, _arc_w, _arc_wxy

Synopsis: 
#include <graph.h> 
short _FAR _arc( short x1, short y1, 
         short x2, short y2, 
         short x3, short y3, 
         short x4, short y4 ); 
short _FAR _arc_w( double x1, double y1, 
          double x2, double y2, 
          double x3, double y3, 
          double x4, double y4 ); 
short _FAR _arc_wxy( struct _wxycoord _FAR *p1, 
           struct _wxycoord _FAR *p2, 
           struct _wxycoord _FAR *p3, 
           struct _wxycoord _FAR *p4 ); 

Description: The _arc functions draw elliptical arcs.  The _arc function uses the view coordinate system.  The _arc_w and _arc_wxy functions use the window coordinate system. 
The center of the arc is the center of the rectangle established by the points (x1,y1) and (x2,y2).  The arc is a segment of the ellipse drawn within this bounding rectangle.  The arc starts at the point on this ellipse that intersects the vector from the centre of the ellipse to the point (x3,y3).  The arc ends at the point on this ellipse that intersects the vector from the centre of the ellipse to the point (x4,y4).  The arc is drawn in a counter-clockwise direction with the current plot action using the current color and the current line style. 
The following picture illustrates the way in which the bounding rectangle and the vectors specifying the start and end points are defined. 
The graphical image cannot be reproduced here.  See the printed version of the manual. 
When the coordinates (x1,y1) and (x2,y2) establish a line or a point (this happens when one or more of the x-coordinates or y-coordinates are equal), nothing is drawn. 
The current output position for graphics output is set to be the point at the end of the arc that was drawn. 

Returns: The _arc functions return a non-zero value when the arc was successfully drawn; otherwise, zero is returned. 

See Also: _ellipse, _pie, _rectangle, _getarcinfo, _setcolor, _setlinestyle, _setplotaction 

Example: 
#include <conio.h> 
#include <graph.h> 
main() 
{ 
  _setvideomode( _VRES16COLOR ); 
  _arc( 120, 90, 520, 390, 500, 20, 450, 460 ); 
  getch(); 
  _setvideomode( _DEFAULTMODE ); 
} 
produces the following: 
The graphical image cannot be reproduced here. See the printed 
version of the manual. 

Classification: PC Graphics 

Systems:  _arc - DOS, QNX 
_arc_w - DOS, QNX 
_arc_wxy - DOS, QNX


### asctime Functions

Synopsis: 
#include <time.h> 
char * asctime( const struct tm *timeptr ); 
char *_asctime( const struct tm *timeptr, char *buf ); 
struct  tm { 
 int tm_sec;  /* seconds after the minute -- [0,61] */ 
 int tm_min;  /* minutes after the hour  -- [0,59] */ 
 int tm_hour;  /* hours after midnight   -- [0,23] */ 
 int tm_mday;  /* day of the month     -- [1,31] */ 
 int tm_mon;  /* months since January   -- [0,11] */ 
 int tm_year;  /* years since 1900          */ 
 int tm_wday;  /* days since Sunday     -- [0,6]  */ 
 int tm_yday;  /* days since January 1   -- [0,365]*/ 
 int tm_isdst; /* Daylight Savings Time flag */ 
}; 

Description: The asctime functions convert the time information in the structure pointed to by timeptr into a string containing exactly 26 characters.  This string has the form shown in the following example: 
    
   Sat Mar 21 15:58:27 1987\n\0 
All fields have a constant width.  The new-line character '\n' and the null character '\0' occupy the last two positions of the string. 
The ANSI function  asctime places the result string in a static buffer that is re-used each time  asctime or  ctime is called.  The non-ANSI function  _asctime places the result string in the buffer pointed to by buf. 

Returns: The asctime functions return a pointer to the character string result. 

See Also: clock, ctime, difftime, gmtime, localtime, mktime, strftime, time, tzset 

Example: 
#include <stdio.h> 
#include <time.h> 
void main() 
 { 
  struct tm  time_of_day; 
  time_t   ltime; 
  auto char  buf[26]; 
  time( &ltime ); 
  _localtime( &ltime, &time_of_day ); 
  printf( "Date and time is: %s\n", 
      _asctime( &time_of_day, buf ) ); 
 } 
produces the following: 
Date and time is: Sat Mar 21 15:58:27 1987 

Classification: ANSI 
_asctime is not ANSI 

Systems:  asctime - All 
_asctime - All


### asin

Synopsis: 
#include <math.h> 
double asin( double x ); 

Description: The asin function computes the principal value of the arcsine of x.  A domain error occurs for arguments not in the range [-1,1]. 

Returns: The asin function returns the arcsine in the range [-P/2,P/2].  When the argument is outside the permissible range, the  matherr function is called.  Unless the default  matherr function is replaced, it will set the global variable  errno to  EDOM, and print a "DOMAIN error" diagnostic message using the  stderr stream. 

See Also: acos, atan, atan2, matherr 

Example: 
#include <stdio.h> 
#include <math.h> 
void main() 
 { 
  printf( "%f\n", asin(.5) ); 
 } 
produces the following: 
0.523599 

Classification: ANSI 

Systems: All


### asinh

Synopsis: 
#include <math.h> 
double asinh( double x ); 

Description: The asinh function computes the inverse hyperbolic sine of x. 

Returns: The asinh function returns the inverse hyperbolic sine value. 

See Also: acosh, atanh, sinh, matherr 

Example: 
#include <stdio.h> 
#include <math.h> 
void main() 
 { 
  printf( "%f\n", asinh( 0.5 ) ); 
 } 
produces the following: 
0.481212 

Classification: WATCOM 

Systems: All


### assert

Synopsis: 
#include <assert.h> 
void assert( int expression ); 

Description: The assert macro prints a diagnostic message upon the  stderr stream and terminates the program if expression is false (0).  The diagnostic message has the form 
Assertion failed:  expression, file filename, line linenumber 
where filename is the name of the source file and linenumber is the line number of the assertion that failed in the source file.  Filename and linenumber are the values of the preprocessing macros  __FILE__ and  __LINE__ respectively.  No action is taken if expression is true (non-zero). 
The  assert macro is typically used during program development to identify program logic errors.  The given expression should be chosen so that it is true when the program is functioning as intended.  After the program has been debugged, the special "no debug" identifier  NDEBUG can be used to remove  assert calls from the program when it is re-compiled.  If  NDEBUG is defined (with any value) with a -d command line option or with a #define directive, the C preprocessor ignores all  assert calls in the program source. 

Returns: The assert macro does not return a value. 

Example: 
#include <stdio.h> 
#include <assert.h> 
void process_string( char *string ) 
 { 
  /* use assert to check argument */ 
  assert( string != NULL ); 
  assert( *string != '\0' ); 
  /* rest of code follows here */ 
 } 
void main() 
 { 
  process_string( "hello" ); 
  process_string( "" ); 
 } 

Classification: ANSI 

Systems: MACRO


### atan

Synopsis: 
#include <math.h> 
double atan( double x ); 

Description: The atan function computes the principal value of the arctangent of x. 

Returns: The atan function returns the arctangent in the range (-P/2,P/2). 

See Also: acos, asin, atan2 

Example: 
#include <stdio.h> 
#include <math.h> 
void main() 
 { 
  printf( "%f\n", atan(.5) ); 
 } 
produces the following: 
0.463648 

Classification: ANSI 

Systems: All


### atan2

Synopsis: 
#include <math.h> 
double atan2( double y, double x ); 

Description: The atan2 function computes the principal value of the arctangent of y/x, using the signs of both arguments to determine the quadrant of the return value.  A domain error occurs if both arguments are zero. 

Returns: The atan2 function returns the arctangent of y/x, in the range (-P,P).  When the argument is outside the permissible range, the  matherr function is called.  Unless the default  matherr function is replaced, it will set the global variable  errno to  EDOM, and print a "DOMAIN error" diagnostic message using the  stderr stream. 

See Also: acos, asin, atan, matherr 

Example: 
#include <stdio.h> 
#include <math.h> 
void main() 
 { 
  printf( "%f\n", atan2( .5, 1. ) ); 
 } 
produces the following: 
0.463648 

Classification: ANSI 

Systems: All


### atanh

Synopsis: 
#include <math.h> 
double atanh( double x ); 

Description: The atanh function computes the inverse hyperbolic tangent of x.  A domain error occurs if the value of x is outside the range (-1,1). 

Returns: The atanh function returns the inverse hyperbolic tangent value.  When the argument is outside the permissible range, the  matherr function is called.  Unless the default  matherr function is replaced, it will set the global variable  errno to  EDOM, and print a "DOMAIN error" diagnostic message using the  stderr stream. 

See Also: acosh, asinh, matherr, tanh 

Example: 
#include <stdio.h> 
#include <math.h> 
void main() 
 { 
  printf( "%f\n", atanh( 0.5 ) ); 
 } 
produces the following: 
0.549306 

Classification: WATCOM 

Systems: All


### atexit

Synopsis: 
#include <stdlib.h> 
int atexit( void (*func)(void) ); 

Description: The atexit function is passed the address of function func to be called when the program terminates normally.  Successive calls to atexit create a list of functions that will be executed on a "last-in, first-out" basis.  No more than 32 functions can be registered with the atexit function. 
The functions have no parameters and do not return values. 

Returns: The atexit function returns zero if the registration succeeds, non-zero if it fails. 

See Also: abort, _exit, exit 

Example: 
#include <stdio.h> 
#include <stdlib.h> 
void main() 
 { 
  void func1(void), func2(void), func3(void); 
  atexit( func1 ); 
  atexit( func2 ); 
  atexit( func3 ); 
  printf( "Do this first.\n" ); 
 } 
void func1(void) { printf( "last.\n" ); } 
void func2(void) { printf( "this " ); } 
void func3(void) { printf( "Do " ); } 
produces the following: 
Do this first. 
Do this last. 

Classification: ANSI 

Systems: All


### atof

Synopsis: 
#include <stdlib.h> 
double atof( const char *ptr ); 

Description: The atof function converts the string pointed to by ptr to double representation.  It is equivalent to 
    
   strtod( ptr, (char **)NULL ) 

Returns: The atof function returns the converted value.  Zero is returned when the input string cannot be converted.  When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

See Also: sscanf, strtod 

Example: 
#include <stdlib.h> 
void main() 
 { 
  double x; 
  x = atof( "3.1415926" ); 
 } 

Classification: ANSI 

Systems: All


### atoi

Synopsis: 
#include <stdlib.h> 
int atoi( const char *ptr ); 

Description: The atoi function converts the string pointed to by ptr to int representation. 

Returns: The atoi function returns the converted value. 

See Also: sscanf, strtol 

Example: 
#include <stdlib.h> 
void main() 
 { 
  int x; 
  x = atoi( "-289" ); 
 } 

Classification: ANSI 

Systems: All


### atol

Synopsis: 
#include <stdlib.h> 
long int atol( const char *ptr ); 

Description: The atol function converts the string pointed to by ptr to long int representation. 

Returns: The atol function returns the converted value. 

See Also: sscanf, strtol 

Example: 
#include <stdlib.h> 
void main() 
 { 
  long int x; 
  x = atol( "-289" ); 
 } 

Classification: ANSI 

Systems: All


### bdos

Synopsis: 
int bdos( int dos_func, unsigned dx, unsigned char al ); 
#include <dos.h> 

Description: The bdos function causes the computer's central processor (CPU) to be interrupted with an interrupt number hexadecimal 21 (0x21), which is a request to invoke a specific DOS function.  Before the interrupt, the DX register is loaded from dx, the AH register is loaded with the DOS function number from dos_func and the AL register is loaded from al.  The remaining registers are passed unchanged to DOS. 
You should consult the technical documentation for the DOS operating system you are using to determine the expected register contents before and after the interrupt in question. 

Returns: The function returns the value of the AX register after the interrupt has completed. 

See Also: int386, int386x, int86, int86x, intdos, intdosx, intr, segread 

Example: 
#include <dos.h> 
#define DISPLAY_OUTPUT  2 
void main() 
 { 
  int rc; 
  rc = bdos( DISPLAY_OUTPUT, 'B', 0 ); 
  rc = bdos( DISPLAY_OUTPUT, 'D', 0 ); 
  rc = bdos( DISPLAY_OUTPUT, 'O', 0 ); 
  rc = bdos( DISPLAY_OUTPUT, 'S', 0 ); 
 } 

Classification: DOS 

Systems: DOS, Win, NT, DOS/PM


### _beginthread

Synopsis: 
#include <process.h> 
int __far _beginthread( 
       void (__far *start_address)(void __far *), 
       void __far *stack_bottom, 
       unsigned stack_size, 
       void __far *arglist ); 

Description: The _beginthread function uses the OS/2 function  DosCreateThread to begin a new thread of execution at the function identified by start_address with a single parameter identified by arglist. 
The new thread will use the memory identified by stack_bottom and stack_size for its stack. 
Note for 16-bit applications:  If the stack is not in DGROUP (i.e., the stack pointer does not point to an area in DGROUP) then you must compile your application with the "zu" option.  For example, the pointer returned by  malloc in a large data model may not be in DGROUP.  The "zu" option relaxes the restriction that the SS register contains the base address of the default data segment, "DGROUP".  Normally, all data items are placed into the group DGROUP and the SS register contains the base address of this group.  In a thread, the SS register will likely not contain the base address of this group.  When the "zu" option is selected, the SS register is volatile (assumed to point to another segment) and any global data references require loading a segment register such as DS with the base address of DGROUP. 
The thread ends when it exits from its main function or calls  exit,  _exit or  _endthread. 

Returns: The _beginthread function returns the thread id for the new thread if successful.  A return value of -1 indicates that the thread could not be started. 

See Also: _endthread 

Example: 
#include <stdio.h> 
#include <stdlib.h> 
#include <process.h> 
#define  STACK_SIZE  4096 
#if defined(__386__) 
 #define FAR 
#else 
 #define FAR __far 
#endif 
void FAR child( void FAR *parm ) 
 { 
  char * FAR *argv = (char * FAR *) parm; 
  int  i; 
  for( i = 0; argv[i]; i++ ) { 
   printf( "argv[%d] = %s\n", i, argv[i] ); 
  } 
  _endthread(); 
 } 
void main() 
 { 
  char *stack; 
  char *args[3]; 
  int  tid; 
  args[0] = "child"; 
  args[1] = "parm"; 
  args[2] = NULL; 
  stack = (char *) malloc( STACK_SIZE ); 
  tid = _beginthread( child, stack, STACK_SIZE, args ); 
 } 

Classification: OS/2 

Systems: OS/2 1.x(MT), OS/2 1.x(DL), OS/2 2.x, NT


### bessel Functions

Synopsis: 
#include <math.h> 
double j0( double x ); 
double j1( double x ); 
double jn( int n, double x ); 
double y0( double x ); 
double y1( double x ); 
double yn( int n, double x ); 

Description: Functions  j0,  j1, and  jn return Bessel functions of the first kind. 
Functions  y0,  y1, and  yn return Bessel functions of the second kind.  The argument x must be positive.  If x is negative,  _matherr will be called to print a DOMAIN error message to  stderr, set  errno to  EDOM, and return the value -HUGE_VAL.  This error handling can be modified by using the  matherr routine. 

Returns: These functions return the result of the desired Bessel function of x. 

See Also: matherr 

Example: 
#include <stdio.h> 
#include <math.h> 
void main() 
 { 
   double x, y, z; 
   x = j0( 2.4 ); 
   y = y1( 1.58 ); 
   z = jn( 3, 2.4 ); 
   printf( "j0(2.4) = %f, y1(1.58) = %f\n", x, y ); 
   printf( "jn(3,2.4) = %f\n", z ); 
 } 

Classification: WATCOM 

Systems:  j0 - All 
j1 - All 
jn - All 
y0 - All 
y1 - All 
yn - All


### _bfreeseg

Synopsis: 
#include <malloc.h> 
int _bfreeseg( __segment seg ); 

Description: The _bfreeseg function frees a based-heap segment. 
The argument seg indicates the segment returned by an earlier call to  _bheapseg. 

Returns: The _bfreeseg function returns 0 if successful and -1 if an error occurred. 

See Also: _bheapseg, calloc, _expand, free, malloc, realloc 

Example: 
#include <stdio.h> 
#include <stdlib.h> 
#include <malloc.h> 
struct list { 
  struct list __based(__self) *next; 
  int     value; 
}; 
void main() 
 { 
  int     i; 
  __segment  seg; 
  struct list __based(seg) *head; 
  struct list __based(seg) *p; 
  /* allocate based heap */ 
  seg = _bheapseg( 1024 ); 
  if( seg == _NULLSEG ) { 
   printf( "Unable to allocate based heap\n" ); 
   exit( 1 ); 
  } 
  /* create a linked list in the based heap */ 
  head = 0; 
  for( i = 1; i < 10; i++ ) { 
   p = _bmalloc( seg, sizeof( struct list ) ); 
   if( p == _NULLOFF ) { 
    printf( "_bmalloc failed\n" ); 
    break; 
   } 
   p->next = head; 
   p->value = i; 
   head = p; 
  } 
  /* traverse the linked list, printing out values */ 
  for( p = head; p != 0; p = p->next ) { 
   printf( "Value = %d\n", p->value ); 
  } 
  /* free all the elements of the linked list */ 
  for( ; p = head; ) { 
   head = p->next; 
   _bfree( seg, p ); 
  } 
  /* free the based heap */ 
  _bfreeseg( seg ); 
 } 

Classification: WATCOM 

Systems: DOS/16, Win/16, QNX/16, OS/2 1.x(all)


### _bgetcmd

Synopsis: 
#include <process.h> 
int _bgetcmd( char *cmd_line, int len ); 

Description: The _bgetcmd function causes the command line information, with the program name removed, to be copied to cmd_line.  The argument len specifies the size of cmd_line.  The information is terminated with a '\0' character.  This provides a method of obtaining the original parameters to a program unchanged (with the white space intact). 
This information can also be obtained by examining the vector of program parameters passed to the main function in the program. 

Returns: If cmd_line is NULL then the number of bytes required to store the command line, excluding the terminating NULL character, is returned; otherwise the number of bytes stored in cmd_line, excluding the terminating NULL character, is returned. 

See Also: abort, atexit, exec Functions, exit, _exit, getcmd, getenv, main, onexit, putenv, spawn Functions, system 

Example: 
Suppose a program were invoked with the command line 
    
   myprog arg-1 ( my  stuff ) here 
where that program contains 
#include <stdio.h> 
#include <stdlib.h> 
#include <process.h> 
void main() 
 { 
  char *cmdline; 
  int  cmdlen; 
  cmdlen = _bgetcmd( NULL, 0 ) + 1; 
  cmdline = malloc( cmdlen ); 
  if( cmdline != NULL ) { 
   cmdlen = _bgetcmd( cmdline, cmdlen ); 
   printf( "%s\n", cmdline ); 
  } 
 } 
produces the following: 
 arg-1 ( my  stuff ) here 

Classification: WATCOM 

Systems: All


### _bheapseg

Synopsis: 
#include <malloc.h> 
__segment _bheapseg( size_t size ); 

Description: The _bheapseg function allocates a based-heap segment of at least size bytes. 
The argument size indicates the initial size for the heap.  The heap will automatically be enlarged as needed if there is not enough space available within the heap to satisfy an allocation request by  _bcalloc,  _bexpand,  _bmalloc, or  _brealloc. 
The value returned by _bheapseg is the segment value or selector for the based heap.  This value must be saved and used as an argument to other based heap functions to indicate which based heap to operate upon. 
Each call to _bheapseg allocates a new based heap. 

Returns: The value returned by _bheapseg is the segment value or selector for the based heap.  This value must be saved and used as an argument to other based heap functions to indicate which based heap to operate upon.  A special value of  _NULLSEG is returned if the segment could not be allocated. 

See Also: _bfreeseg, calloc, _expand, malloc, realloc 

Example: 
#include <stdio.h> 
#include <stdlib.h> 
#include <malloc.h> 
struct list { 
  struct list __based(__self) *next; 
  int     value; 
}; 
void main() 
 { 
  int     i; 
  __segment  seg; 
  struct list __based(seg) *head; 
  struct list __based(seg) *p; 
  /* allocate based heap */ 
  seg = _bheapseg( 1024 ); 
  if( seg == _NULLSEG ) { 
   printf( "Unable to allocate based heap\n" ); 
   exit( 1 ); 
  } 
  /* create a linked list in the based heap */ 
  head = 0; 
  for( i = 1; i < 10; i++ ) { 
   p = _bmalloc( seg, sizeof( struct list ) ); 
   if( p == _NULLOFF ) { 
    printf( "_bmalloc failed\n" ); 
    break; 
   } 
   p->next = head; 
   p->value = i; 
   head = p; 
  } 
  /* traverse the linked list, printing out values */ 
  for( p = head; p != 0; p = p->next ) { 
   printf( "Value = %d\n", p->value ); 
  } 
  /* free all the elements of the linked list */ 
  for( ; p = head; ) { 
   head = p->next; 
   _bfree( seg, p ); 
  } 
  /* free the based heap */ 
  _bfreeseg( seg ); 
 } 

Classification: WATCOM 

Systems: DOS/16, Win/16, QNX/16, OS/2 1.x(all)


### _bios_disk

Synopsis: 
#include <bios.h> 
unsigned short _bios_disk( unsigned service, 
              struct diskinfo_t *diskinfo ); 
struct  diskinfo_t {     /* disk parameters  */ 
    unsigned drive;   /* drive number    */ 
    unsigned head;    /* head number    */ 
    unsigned track;   /* track number    */ 
    unsigned sector;   /* sector number   */ 
    unsigned nsectors;  /* number of sectors */ 
    void __far *buffer; /* buffer address   */ 
}; 

Description: The _bios_disk function uses INT 0x13 to provide access to the BIOS disk functions.  Information for the desired service is passed the diskinfo_t structure pointed to by diskinfo.  The value for service can be one of the following values: 

_DISK_RESET Forces the disk controller to do a reset on the disk.  This request does not use the diskinfo argument. 

_DISK_STATUS Obtains the status of the last disk operation. 

_DISK_READ Reads the specified number of sectors from the disk.  This request uses all of the information passed in the diskinfo structure. 

_DISK_WRITE Writes the specified amount of data to the disk.  This request uses all of the information passed in the diskinfo structure. 

_DISK_VERIFY Checks the disk to be sure the specified sectors exist and can be read.  A CRC (cyclic redundancy check) test is performed.  This request uses all of the information passed in the diskinfo structure except for the buffer field. 

_DISK_FORMAT Formats the specified track on the disk.  The head and track fields indicate the track to be formatted.  Only one track can be formatted per call.  The buffer field points to a set of sector markers, whose format depends on the type of disk drive.  This service has no return value. 

Returns: The _bios_disk function returns status information in the high-order byte when service is _DISK_STATUS, _DISK_READ, _DISK_WRITE, or _DISK_VERIFY.  The possible values are: 

0x00 Operation successful 

0x01 Bad command 

0x02 Address mark not found 

0x03 Attempt to write to write-protected disk 

0x04 Sector not found 

0x05 Reset failed 

0x06 Disk changed since last operation 

0x07 Drive parameter activity failed 

0x08 DMA overrun 

0x09 Attempt to DMA across 64K boundary 

0x0A Bad sector detected 

0x0B Bad track detected 

0x0C Unsupported track 

0x10 Data read (CRC/ECC) error 

0x11 CRC/ECC corrected data error 

0x20 Controller failure 

0x40 Seek operation failed 

0x80 Disk timed out or failed to respond 

0xAA Drive not ready 

0xBB Undefined error occurred 

0xCC Write fault occurred 

0xE0 Status error 

0xFF Sense operation failed 

Example: 
#include <stdio.h> 
#include <bios.h> 
void main() 
 { 
  struct diskinfo_t di; 
  unsigned short status; 
  di.drive = di.head = di.track = di.sector = 0; 
  di.nsectors = 1; 
  di.buffer = NULL; 
  status = _bios_disk( _DISK_VERIFY, &di ); 
  printf( "Status = 0x%4.4X\n", status ); 
 } 

Classification: BIOS 

Systems: DOS, Win, NT, DOS/PM


### _bios_equiplist

Synopsis: 
#include <bios.h> 
unsigned short _bios_equiplist( void ); 

Description: The _bios_equiplist function uses INT 0x11 to determine what hardware and peripherals are installed on the machine. 

Returns: The _bios_equiplist function returns a set of bits indicating what is current installed on the machine.  Those bits are defined as follows: 

bit 0 Set to 1 if system boots from disk 

bit 1 Set to 1 if a math coprocessor is installed 

bits 2-3 Indicates motherboard RAM size 

bits 4-5 Initial video mode 

bits 6-7 Number of diskette drives 

bit 8 Set to 1 if machine does not have DMA 

bits 9-11 Number of serial ports 

bit 12 Set to 1 if a game port is attached 

bit 13 Set to 1 if a serial printer is attached 

bits 14-15 Number of parallel printers installed 

Example: 
#include <stdio.h> 
#include <bios.h> 
void main() 
 { 
  unsigned short equipment; 
  equipment = _bios_equiplist(); 
  printf( "Equipment flags = 0x%4.4X\n", equipment ); 
 } 

Classification: BIOS 

Systems: DOS, Win, NT, DOS/PM


### _bios_keybrd

Synopsis: 
#include <bios.h> 
unsigned short _bios_keybrd( unsigned service ); 

Description: The _bios_keybrd function uses INT 0x16 to access the BIOS keyboard services.  The possible values for service are the following constants: 

_KEYBRD_READ Reads the next character from the keyboard.  The function will wait until a character has been typed. 

_KEYBRD_READY Checks to see if a character has been typed.  If there is one, then its value will be returned, but it is not removed from the input buffer. 

_KEYBRD_SHIFTSTATUS Returns the current state of special keys. 

_NKEYBRD_READ Reads the next character from an enhanced keyboard.  The function will wait until a character has been typed. 

_NKEYBRD_READY Checks to see if a character has been typed on an enhanced keyboard.  If there is one, then its value will be returned, but it is not removed from the input buffer. 

_NKEYBRD_SHIFTSTATUS Returns the current state of special keys on an enhanced keyboard. 

Returns: The return value depends on the service requested. 
The _KEYBRD_READ and _NKEYBRD_READ services return the character's ASCII value in the low-order byte and the character's keyboard scan code in the high-order byte. 
The _KEYBRD_READY and _NKEYBRD_READY services return zero if there was no character available, otherwise it returns the same value returned by _KEYBRD_READ and _NKEYBRD_READ. 
The shift status is returned in the low-order byte with one bit for each special key defined as follows: 

bit 0 (0x01) Right SHIFT key is pressed 

bit 1 (0x02) Left SHIFT key is pressed 

bit 2 (0x04) CTRL key is pressed 

bit 3 (0x08) ALT key is pressed 

bit 4 (0x10) SCROLL LOCK is on 

bit 5 (0x20) NUM LOCK is on 

bit 6 (0x40) CAPS LOCK is on 

bit 7 (0x80) Insert mode is set 

Example: 
#include <stdio.h> 
#include <bios.h> 
void main() 
 { 
  unsigned short key_state; 
  key_state = _bios_keybrd( _KEYBRD_SHIFTSTATUS ); 
  if( key_state & 0x10 ) 
    printf( "SCROLL LOCK is on\n" ); 
  if( key_state & 0x20 ) 
    printf( "NUM LOCK is on\n" ); 
  if( key_state & 0x40 ) 
    printf( "CAPS LOCK is on\n" ); 
 } 
produces the following: 
NUM LOCK is on 

Classification: BIOS 

Systems: DOS, Win, NT, DOS/PM


### _bios_memsize

Synopsis: 
#include <bios.h> 
unsigned short _bios_memsize( void ); 

Description: The _bios_memsize function uses INT 0x12 to determine the total amount of memory available. 

Returns: The _bios_memsize function returns the total amount of 1K blocks of memory installed (maximum 640). 

Example: 
#include <stdio.h> 
#include <bios.h> 
void main() 
 { 
  unsigned short memsize; 
  memsize = _bios_memsize(); 
  printf( "The total amount of memory is: %dK\n", 
        memsize ); 
 } 
produces the following: 
The total amount of memory is: 640K 

Classification: BIOS 

Systems: DOS, Win, NT, DOS/PM


### _bios_printer

Synopsis: 
#include <bios.h> 
unsigned short _bios_printer( unsigned service, 
               unsigned port, 
               unsigned data ); 

Description: The _bios_printer function uses INT 0x17 to perform printer output services to the printer specified by port.  The values for service are: 

_PRINTER_WRITE Sends the low-order byte of data to the printer specified by port. 

_PRINTER_INIT Initializes the printer specified by port. 

_PRINTER_STATUS Get the status of the printer specified by port. 

Returns: The _bios_printer function returns a printer status byte defined as follows: 

bit 0 (0x01) Printer timed out 

bits 1-2 Unused 

bit 3 (0x08) I/O error 

bit 4 (0x10) Printer selected 

bit 5 (0x20) Out of paper 

bit 6 (0x40) Printer acknowledge 

bit 7 (0x80) Printer not busy 

Example: 
#include <stdio.h> 
#include <bios.h> 
void main() 
 { 
  unsigned short status; 
  status = _bios_printer( _PRINTER_STATUS, 1, 0 ); 
  printf( "Printer status: 0x%2.2X\n", status ); 
 } 

Classification: BIOS 

Systems: DOS, Win, NT, DOS/PM


### _bios_serialcom

Synopsis: 
#include <bios.h> 
unsigned short _bios_serialcom( unsigned service, 
                unsigned serial_port, 
                unsigned data ); 

Description: The _bios_serialcom function uses INT 0x14 to provide serial communications services to the serial port specified by serial_port.  0 represents COM1, 1 represents COM2, etc.  The values for service are: 

_COM_INIT Initializes the serial port to the parameters specified in data. 

_COM_SEND Transmits the low-order byte of data to the serial port. 

_COM_RECEIVE Reads an input character from the serial port. 

_COM_STATUS Returns the current status of the serial port. 
The value passed in data for the _COM_INIT service can be built using the appropriate combination of the following values: 

_COM_110 110 baud 

_COM_150 150 baud 

_COM_300 300 baud 

_COM_600 600 baud 

_COM_1200 1200 baud 

_COM_2400 2400 baud 

_COM_4800 4800 baud 

_COM_9600 9600 baud 

_COM_NOPARITY No parity 

_COM_EVENPARITY Even parity 

_COM_ODDPARITY Odd parity 

_COM_CHR7 7 data bits 

_COM_CHR8 8 data bits 

_COM_STOP1 1 stop bit 

_COM_STOP2 2 stop bits 

Returns: The _bios_serialcom function returns a 16-bit value with the high-order byte containing status information defined as follows: 

bit 15 (0x8000) Timed out 

bit 14 (0x4000) Transmit shift register empty 

bit 13 (0x2000) Transmit holding register empty 

bit 12 (0x1000) Break detected 

bit 11 (0x0800) Framing error 

bit 10 (0x0400) Parity error 

bit 9 (0x0200) Overrun error 

bit 8 (0x0100) Data ready 
The low-order byte of the return value depends on the value of the service argument. 
When service is _COM_SEND, bit 15 will be set if the data could not be sent.  If bit 15 is clear, the return value equals the byte sent. 
When service is _COM_RECEIVE, the byte read will be returned in the low-order byte if there was no error.  If there was an error, at least one of the high-order status bits will be set. 
When service is _COM_INIT or _COM_STATUS the low-order bits are defined as follows: 

bit 0 (0x01) Clear to send (CTS) changed 

bit 1 (0x02) Data set ready changed 

bit 2 (0x04) Trailing-edge ring detector 

bit 3 (0x08) Receive line signal detector changed 

bit 4 (0x10) Clear to send 

bit 5 (0x20) Data-set ready 

bit 6 (0x40) Ring indicator 

bit 7 (0x80) Receive-line signal detected 

Example: 
#include <stdio.h> 
#include <bios.h> 
void main() 
 { 
  unsigned short status; 
  status = _bios_serialcom( _COM_STATUS, 1, 0 ); 
  printf( "Serial status: 0x%2.2X\n", status ); 
 } 

Classification: BIOS 

Systems: DOS, Win, NT, DOS/PM


### _bios_timeofday

Synopsis: 
#include <bios.h> 
int _bios_timeofday( int service, long *timeval ); 

Description: The _bios_timeofday function uses INT 0x1A to get or set the current system clock value.  The values for service are: 

_TIME_GETCLOCK Places the current system clock value in the location pointed to by timeval.  The function returns zero if midnight has not passed since the last time the system clock was read or set; otherwise, it returns 1. 

_TIME_SETCLOCK Sets the system clock to the value in the location pointed to by timeval. 

Returns: A value of -1 is returned if neither _TIME_GETCLOCK nor _TIME_SETCLOCK were specified; otherwise 0 is returned. 

Example: 
#include <stdio.h> 
#include <bios.h> 
void main() 
 { 
  long time_of_day; 
  _bios_timeofday( _TIME_GETCLOCK, &time_of_day ); 
  printf( "Ticks since midnight: %lu\n", time_of_day ); 
 } 
produces the following: 
Ticks since midnight: 762717 

Classification: BIOS 

Systems: DOS, Win, NT, DOS/PM


### _bprintf

Synopsis: 
#include <stdio.h> 
int _bprintf( char *buf, unsigned int bufsize, 
       const char *format, ... ); 

Description: The _bprintf function is equivalent to the  sprintf function, except that the argument bufsize specifies the size of the character array buf into which the generated output is placed.  A null character is placed at the end of the generated character string.  The format string is described under the description of the  printf function. 

Returns: The _bprintf function returns the number of characters written into the array, not counting the terminating null character.  An error can occur while converting a value for output.  When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

See Also: cprintf, fprintf, printf, sprintf, _vbprintf, vcprintf, vfprintf, vprintf, vsprintf 

Example: 
#include <stdio.h> 
void main( int argc, char * argv[] ) 
 { 
  char file_name[9]; 
  char file_ext[4]; 
  _bprintf( file_name, 9, "%s", argv[1] ); 
  _bprintf( file_ext,  4, "%s", argv[2] ); 
  printf( "%s.%s\n", file_name, file_ext ); 
 } 

Classification: WATCOM 

Systems: All


### bsearch

Synopsis: 
#include <stdlib.h> 
void *bsearch( const void *key, 
        const void *base, 
        size_t num, 
        size_t width, 
        int (*compar)( const void *pkey, 
               const void *pbase) ); 

Description: The bsearch function performs a binary search of a sorted array of num elements, which is pointed to by base, for an item which matches the object pointed to by key.  Each element in the array is width bytes in size.  The comparison function pointed to by compar is called with two arguments that point to elements in the array.  The first argument pkey points to the same object pointed to by key.  The second argument pbase points to a element in the array.  The comparison function shall return an integer less than, equal to, or greater than zero if the key object is less than, equal to, or greater than the element in the array. 

Returns: The bsearch function returns a pointer to the matching member of the array, or NULL if a matching object could not be found.  If there are multiple values in the array which are equal to the key, the return value is not necessarily the first occurrence of a matching value when the array is searched linearly. 

See Also: lfind, lsearch, qsort 

Example: 
#include <stdio.h> 
#include <stdlib.h> 
#include <string.h> 
static const char *keywords[] = { 
    "auto", 
    "break", 
    "case", 
    "char", 
    /* . */ 
    /* . */ 
    /* . */ 
    "while" 
 }; 
#define NUM_KW  sizeof(keywords) / sizeof(char *) 
int kw_compare( const void *p1, const void *p2 ) 
 { 
  const char *p1c = (const char *) p1; 
  const char **p2c = (const char **) p2; 
  return( strcmp( p1c, *p2c ) ); 
 } 
int keyword_lookup( const char *name ) 
 { 
  const char **key; 
  key = (char const **) bsearch( name, keywords, NUM_KW, 
          sizeof( char * ),  kw_compare ); 
  if( key == NULL ) return( -1 ); 
  return key - keywords; 
 } 
void main() 
 { 
  printf( "%d\n", keyword_lookup( "case" ) ); 
  printf( "%d\n", keyword_lookup( "crigger" ) ); 
  printf( "%d\n", keyword_lookup( "auto" ) ); 
 } 
//************ Sample program output ************ 
//2 
//-1 
//0 
produces the following: 
2 
-1 
0 

Classification: ANSI 

Systems: All


### cabs

Synopsis: 
#include <math.h> 
double cabs( struct complex value ); 
struct _complex { 
  double  x;  /* real part */ 
  double  y;  /* imaginary part */ 
}; 

Description: The cabs function computes the absolute value of the complex number value by a calculation which is equivalent to 
sqrt( (value.x*value.x) + (value.y*value.y) ) 
In certain cases, overflow errors may occur which will cause the  matherr routine to be invoked. 

Returns: The absolute value is returned. 

Example: 
#include <stdio.h> 
#include <math.h> 
struct _complex c = { -3.0, 4.0 }; 
void main() 
 { 
  printf( "%f\n", cabs( c ) ); 
 } 
produces the following: 
5.000000 

Classification: WATCOM 

Systems: All


### calloc Functions

Synopsis: 
#include <stdlib.h>  For ANSI compatibility (calloc only) 
#include <malloc.h>  Required for other function prototypes 
void *calloc( size_t n, size_t size ); 
void __based(void) *_bcalloc( __segment seg, 
               size_t n, 
               size_t size ); 
void __far  *_fcalloc( size_t n, size_t size ); 
void __near *_ncalloc( size_t n, size_t size ); 

Description: The calloc functions allocate space for an array of n objects, each of length size bytes.  Each element is initialized to 0. 
Each function allocates memory from a particular heap, as listed below: 

calloc Depends on data model of the program 

_bcalloc Based heap specified by seg value 

_fcalloc Far heap (outside the default data segment) 

_ncalloc Near heap (inside the default data segment) 
In a small data memory model, the  calloc function is equivalent to the  _ncalloc function; in a large data memory model, the  calloc function is equivalent to the  _fcalloc function. 
A block of memory allocated should be freed using the appropriate  free function. 

Returns: The calloc functions return a pointer to the start of the allocated memory.  The return value is NULL (_NULLOFF for  _bcalloc) if there is insufficient memory available or if the value of the size argument is zero. 

See Also: _expand Functions, free Functions, halloc, hfree, malloc Functions, _msize Functions, realloc Functions, sbrk 

Example: 
#include <stdlib.h> 
void main() 
 { 
  char *buffer; 
  buffer = (char *)calloc( 80, sizeof(char) ); 
 } 

Classification: calloc is ANSI; _bcalloc, _fcalloc, _ncalloc are not ANSI 

Systems:  calloc - All 
_bcalloc - DOS/16, Win/16, QNX/16, OS/2 1.x(all) 
_fcalloc - DOS/16, Win/16, QNX/16, OS/2 1.x(all) 
_ncalloc - DOS, Win, QNX, OS/2 1.x, OS/2 1.x(MT), OS/2 2.x, NT


### ceil

Synopsis: 
#include <math.h> 
double ceil( double x ); 

Description: The ceil function (ceiling function) computes the smallest integer not less than x. 

Returns: The ceil function returns the smallest integer not less than x, expressed as a double. 

See Also: floor 

Example: 
#include <stdio.h> 
#include <math.h> 
void main() 
 { 
  printf( "%f %f %f %f %f\n", ceil( -2.1 ), ceil( -2. ), 
    ceil( 0.0 ), ceil( 2. ), ceil( 2.1 ) ); 
 } 
produces the following: 
-2.000000 -2.000000 0.000000 2.000000 3.000000 

Classification: ANSI 

Systems: All


### cgets

Synopsis: 
#include <conio.h> 
char *cgets( char *buf ); 

Description: The cgets function gets a string of characters directly from the console and stores the string and its length in the array pointed to by buf.  The first element of the array buf[0] must contain the maximum length in characters of the string to be read.  The array must be big enough to hold the string, a terminating null character, and two additional bytes. 
The cgets function reads characters until a carriage-return line-feed combination is read, or until the specified number of characters is read.  The string is stored in the array starting at buf[2].  The carriage-return line-feed combination, if read, is replaced by a null character.  The actual length of the string read is placed in buf[1]. 

Returns: The cgets function returns a pointer to the start of the string which is at buf[2]. 

See Also: fgets, getch, getche, gets 

Example: 
#include <conio.h> 
void main() 
 { 
  char buffer[82]; 
  buffer[0] = 80; 
  cgets( buffer ); 
  cprintf( "%s\r\n", &buffer[2] ); 
 } 

Classification: WATCOM 

Systems: All


### _chain_intr

Synopsis: 
void _chain_intr( void (__interrupt __far *func)() ); 
#include <dos.h> 

Description: The _chain_intr function is used at the end of an interrupt routine to start executing another interrupt handler (usually the previous handler for that interrupt).  When the interrupt handler designated by func receives control, the stack and registers appear as though the interrupt just occurred. 

Returns: The _chain_intr function does not return. 

See Also: _dos_getvect, _dos_keep, _dos_setvect 

Example: 
#include <stdio.h> 
#include <dos.h> 
volatile int clock_ticks; 
void (__interrupt __far *prev_int_1c)(); 
#define BLIP_COUNT  (5*18)  /* 5 seconds */ 
void __interrupt __far timer_rtn() 
 { 
  ++clock_ticks; 
  _chain_intr( prev_int_1c ); 
 } 
int delays = 0; 
int compile_a_line() 
 { 
  if( delays > 15 ) return( 0 ); 
  delay( 1000 );  /* delay for 1 second */ 
  printf( "Delayed for 1 second\n" ); 
  delays++; 
  return( 1 ); 
 } 
void main() 
 { 
  prev_int_1c = _dos_getvect( 0x1c ); 
  _dos_setvect( 0x1c, timer_rtn ); 
  while( compile_a_line() ) { 
    if( clock_ticks >= BLIP_COUNT ) { 
      putchar( '.' ); 
      clock_ticks -= BLIP_COUNT; 
    } 
  } 
  _dos_setvect( 0x1c, prev_int_1c ); 
 } 

Classification: WATCOM 

Systems: DOS, Win/16


### chdir

Synopsis: 
#include <sys\types.h> 
#include <direct.h> 
int chdir( const char *path ); 

Description: The chdir function changes the current directory on the specified drive to the specified path.  If no drive is specified in path then the current drive is assumed.  The path can be either relative to the current directory on the specified drive or it can be an absolute path name. 
Each drive under DOS, OS/2 or Windows NT has a current directory.  The current working directory is the current directory of the current drive.  If you wish to change the current drive, you must use the  _dos_setdrive function. 

Returns: The chdir function returns zero if successful.  Otherwise, -1 is returned,  errno is set to indicate the error, and the current working directory remains unchanged. 

Errors: When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

ENOENT The specified path does not exist or path is an empty string. 

See Also: _dos_setdrive, getcwd, mkdir, rmdir 

Example: 
#include <stdio.h> 
#include <stdlib.h> 
#include <direct.h> 
void main( int argc, char *argv[] ) 
 { 
  if( argc != 2 ) { 
   fprintf( stderr, "Use: cd <directory>\n" ); 
   exit( 1 ); 
  } 
  if( chdir( argv[1] ) == 0 ) { 
   printf( "Directory changed to %s\n", argv[1] ); 
   exit( 0 ); 
  } else { 
   perror( argv[1] ); 
   exit( 1 ); 
  } 
 } 

Classification: POSIX 1003.1 

Systems: All


### chmod

Synopsis: 
#include <sys\types.h> 
#include <sys\stat.h> 
#include <io.h> 
int chmod( const char *path, int permission ); 

Description: The chmod function changes the permissions for a file specified by path to be the settings in the mode given by permission.  The access permissions for the file or directory are specified as a combination of bits (defined in the <sys\stat.h> header file). 
The following bits define permissions for the owner. 

S_IRWXU Read, write, execute/search 

S_IRUSR Read permission 

S_IWUSR Write permission 

S_IXUSR Execute/search permission 
The following bits define permissions for the group. 

S_IRWXG Read, write, execute/search 

S_IRGRP Read permission 

S_IWGRP Write permission 

S_IXGRP Execute/search permission 
The following bits define permissions for others. 

S_IRWXO Read, write, execute/search 

S_IROTH Read permission 

S_IWOTH Write permission 

S_IXOTH Execute/search permission 
The following bits define miscellaneous permissions used by other implementations. 

S_IREAD is equivalent to S_IRUSR (read permission) 

S_IWRITE is equivalent to S_IWUSR (write permission) 

S_IEXEC is equivalent to S_IXUSR (execute/search permission) 
The following bits may also be specified in permission. 

S_ISUID set user id on execution 

S_ISGID set group id on execution 
If the calling process does not have appropriate privileges, and if the group ID of the file does not match the effective group ID or one of the supplementary group IDs, and if the file is a regular file, bit S_ISGID (set group ID on execution) in the file's mode shall be cleared upon successful return from the chmod function. 
Upon successful completion, the chmod function will mark for update the st_ctime field of the file. 

Returns: The chmod returns zero if the new settings are successfully made; otherwise, -1 is returned and  errno is set to indicate the error. 

Errors: When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

EACCES Search permission is denied for a component of path. 

ENOENT The specified path does not exist or path is an empty string. 

See Also: fstat, open, sopen, stat 

Example: 
/* 
 * change the permissions of a list of files 
 * to be read/write by the owner only 
 */ 
#include <stdio.h> 
#include <stdlib.h> 
#include <sys\types.h> 
#include <sys\stat.h> 
#include <io.h> 
void main( int argc, char *argv[] ) 
 { 
  int i; 
  int ecode = 0; 
  for( i = 1; i < argc; i++ ) { 
   if( chmod( argv[i], S_IRUSR | S_IWUSR ) == -1 ) { 
    perror( argv[i] ); 
    ecode++; 
   } 
  } 
  exit( ecode ); 
 } 

Classification: POSIX 1003.1 

Systems: All


### chsize

Synopsis: 
#include <io.h> 
int chsize( int handle, long size ); 

Description: The chsize function changes the size of the file associated with handle by extending or truncating the file to the length specified by size.  If the file needs to be extended, the file is padded with NULL ('\0') characters. 

Returns: The chsize function returns zero if successful.  A return value of -1 indicates an error, and  errno is set to indicate the error. 

Errors: When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

EBADF Invalid file handle. 

ENOSPC Not enough space left on the device to extend the file. 

See Also: close, creat, open 

Example: 
#include <stdio.h> 
#include <io.h> 
#include <fcntl.h> 
#include <sys\stat.h> 
void main() 
 { 
  int  handle; 
  handle = open( "file", O_RDWR | O_CREAT, 
        S_IRUSR | S_IWUSR | S_IRGRP | S_IWGRP ); 
  if( handle != -1 ) { 
   if( chsize( handle, 32 * 1024L ) != 0 ) { 
     printf( "Error extending file\n" ); 
   } 
   close( handle ); 
  } 
 } 

Classification: WATCOM 

Systems: All


### _clear87

Synopsis: 
#include <float.h> 
unsigned int _clear87( void ); 

Description: The _clear87 function clears the floating-point status word which is used to record the status of 8087/80287/80387/80486 floating-point operations. 

Returns: The _clear87 function returns the old floating-point status.  The description of this status is found in the <float.h> header file. 

See Also: _control87, _fpreset, _status87 

Example: 
#include <stdio.h> 
#include <float.h> 
void main() 
 { 
  unsigned int fp_status; 
  fp_status = _clear87(); 
  printf( "80x87 status =" ); 
  if( fp_status & SW_INVALID ) 
    printf( " invalid" ); 
  if( fp_status & SW_DENORMAL ) 
    printf( " denormal" ); 
  if( fp_status & SW_ZERODIVIDE ) 
    printf( " zero_divide" ); 
  if( fp_status & SW_OVERFLOW ) 
    printf( " overflow" ); 
  if( fp_status & SW_UNDERFLOW ) 
    printf( " underflow" ); 
  if( fp_status & SW_INEXACT ) 
    printf( " inexact_result" ); 
  printf( "\n" ); 
 } 

Classification: Intel 

Systems: All


### clearenv

Synopsis: 
int clearenv( void ); 
#include <env.h> 

Description: The clearenv function clears the process environment area.  No environment variables are defined immediately after a call to the clearenv function.  Note that this clears the  PATH,  COMSPEC, and  TZ environment variables which may then affect the operation of other library functions. 
The clearenv function may manipulate the value of the pointer  environ. 

Returns: The clearenv function returns zero upon successful completion.  Otherwise, it will return a non-zero value and set  errno to indicate the error. 

Errors: When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

ENOMEM Not enough memory to allocate a control structure. 

See Also: exec Functions, getenv, putenv, _searchenv, setenv, spawn Functions, system 

Example: 
The following example clears the entire environment area and sets up a new TZ environment variable. 
#include <env.h> 
void main() 
 { 
  clearenv(); 
  setenv( "TZ", "EST5EDT", 0 ); 
 } 

Classification: POSIX 1003.1 

Systems: All


### clearerr

Synopsis: 
#include <stdio.h> 
void clearerr( FILE *fp ); 

Description: The clearerr function clears the end-of-file and error indicators for the stream pointed to by fp.  These indicators are cleared only when the file is opened or by an explicit call to the  clearerr or  rewind functions. 

Returns: The clearerr function returns no value. 

See Also: feof, ferror, perror 

Example: 
#include <stdio.h> 
void main() 
 { 
  FILE *fp; 
  int c; 
  c = 'J'; 
  fp = fopen( "file", "w" ); 
  if( fp != NULL ) { 
   fputc( c, fp ); 
   if( ferror( fp ) ) {  /* if error     */ 
     clearerr( fp );  /* clear the error */ 
     fputc( c, fp );  /* and retry it   */ 
   } 
  } 
 } 

Classification: ANSI 

Systems: All


### _clearscreen

Synopsis: 
#include <graph.h> 
void _FAR _clearscreen( short area ); 

Description: The _clearscreen function clears the indicated area and fills it with the background color.  The area argument must be one of the following values: 

_GCLEARSCREEN area is entire screen 

_GVIEWPORT area is current viewport or clip region 

_GWINDOW area is current text window 

Returns: The _clearscreen function does not return a value. 

See Also: _setbkcolor, _setviewport, _setcliprgn, _settextwindow 

Example: 
#include <conio.h> 
#include <graph.h> 
main() 
{ 
  _setvideomode( _VRES16COLOR ); 
  _rectangle( _GFILLINTERIOR, 100, 100, 540, 380 ); 
  getch(); 
  _setviewport( 200, 200, 440, 280 ); 
  _clearscreen( _GVIEWPORT ); 
  getch(); 
  _setvideomode( _DEFAULTMODE ); 
} 

Classification: PC Graphics 

Systems: DOS, QNX


### clock

Synopsis: 
#include <time.h> 
clock_t clock(void); 

Description: The clock function returns the number of clock ticks of processor time used by program since the program started executing.  This can be converted to seconds by dividing by the value of the macro  CLOCKS_PER_SEC. 

Returns: The clock function returns the number of clock ticks that have occurred since the program started executing. 

See Also: asctime, ctime, difftime, gmtime, localtime, mktime, strftime, time, tzset 

Example: 
#include <stdio.h> 
#include <math.h> 
#include <time.h> 
void compute( void ) 
 { 
  int i, j; 
  double x; 
  x = 0.0; 
  for( i = 1; i <= 100; i++ ) 
   for( j = 1; j <= 100; j++ ) 
    x += sqrt( (double) i * j ); 
  printf( "%16.7f\n", x ); 
 } 
void main() 
 { 
  clock_t start_time, end_time; 
  start_time = clock(); 
  compute(); 
  end_time = clock(); 
  printf( "Execution time was %lu seconds\n", 
     (end_time - start_time) / CLOCKS_PER_SEC ); 
 } 

Classification: ANSI 

Systems: All


### close

Synopsis: 
#include <io.h> 
int close( int handle ); 

Description: The close function closes a file at the operating system level.  The handle value is the file handle returned by a successful execution of one of the  creat,  dup,  dup2,  open or  sopen functions. 

Returns: The close function returns zero if successful.  Otherwise, it returns -1 and  errno is set to indicate the error. 

Errors: When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

EBADF The handle argument is not a valid file handle. 

See Also: creat, dup, dup2, open, sopen 

Example: 
#include <fcntl.h> 
#include <io.h> 
void main() 
 { 
  int handle; 
  handle = open( "file", O_RDONLY ); 
  if( handle != -1 ) { 
   /* process file */ 
   close( handle ); 
  } 
 } 

Classification: POSIX 1003.1 

Systems: All


### closedir

Synopsis: 
#include <direct.h> 
int closedir( DIR *dirp ); 

Description: The closedir function closes the directory specified by dirp and frees the memory allocated by  opendir. 

Returns: The closedir function returns zero if successful, non-zero otherwise. 

Errors: When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

EBADF The argument dirp does not refer to an open directory stream. 

See Also: _dos_find Functions, opendir, readdir 

Example: 
To get a list of files contained in the directory \watcom\h on your default disk: 
#include <stdio.h> 
#include <direct.h> 
void main() 
 { 
  DIR *dirp; 
  struct dirent *direntp; 
  dirp = opendir( "\\watcom\\h" ); 
  if( dirp != NULL ) { 
   for(;;) { 
    direntp = readdir( dirp ); 
    if( direntp == NULL ) break; 
    printf( "%s\n", direntp->d_name ); 
   } 
   closedir( dirp ); 
  } 
 } 
Note the use of two adjacent backslash characters (\) within character-string constants to signify a single backslash. 

Classification: POSIX 1003.1 

Systems: All


### _control87

Synopsis: 
#include <float.h> 
unsigned int _control87( unsigned int newcw, 
             unsigned int mask ); 

Description: The _control87 function updates the control word of the 8087/80287/80387/80486.  If mask is zero, then the control word is not updated.  If mask is non-zero, then the control word is updated with bits from newcw corresponding to every bit that is on in mask. 

Returns: The _control87 function returns the new control word.  The description of bits defined for the control word is found in the <float.h> header file. 

See Also: _clear87, _fpreset, _status87 

Example: 
#include <stdio.h> 
#include <float.h> 
char *status[2] = { "disabled", "enabled" }; 
void main() 
 { 
  unsigned int fp_cw = 0; 
  unsigned int fp_mask = 0; 
  unsigned int bits; 
  fp_cw = _control87( fp_cw, 
            fp_mask ); 
  printf( "Interrupt Exception Masks\n" ); 
  bits = fp_cw & MCW_EM; 
  printf( "  Invalid Operation exception %s\n", 
      status[ (bits & EM_INVALID) == 0 ] ); 
  printf( "  Denormalized exception %s\n", 
      status[ (bits & EM_DENORMAL) == 0 ] ); 
  printf( "  Divide-By-Zero exception %s\n", 
      status[ (bits & EM_ZERODIVIDE) == 0 ] ); 
  printf( "  Overflow exception %s\n", 
      status[ (bits & EM_OVERFLOW) == 0 ] ); 
  printf( "  Underflow exception %s\n", 
      status[ (bits & EM_UNDERFLOW) == 0 ] ); 
  printf( "  Precision exception %s\n", 
      status[ (bits & EM_PRECISION) == 0 ] ); 
  printf( "Infinity Control = " ); 
  bits = fp_cw & MCW_IC; 
  if( bits == IC_AFFINE )   printf( "affine\n" ); 
  if( bits == IC_PROJECTIVE ) printf( "projective\n" ); 
  printf( "Rounding Control = " ); 
  bits = fp_cw & MCW_RC; 
  if( bits == RC_NEAR )    printf( "near\n" ); 
  if( bits == RC_DOWN )    printf( "down\n" ); 
  if( bits == RC_UP )     printf( "up\n" ); 
  if( bits == RC_CHOP )    printf( "chop\n" ); 
  printf( "Precision Control = " ); 
  bits = fp_cw & MCW_PC; 
  if( bits == PC_24 )     printf( "24 bits\n" ); 
  if( bits == PC_53 )     printf( "53 bits\n" ); 
  if( bits == PC_64 )     printf( "64 bits\n" ); 
 } 

Classification: Intel 

Systems: All


### cos

Synopsis: 
#include <math.h> 
double cos( double x ); 

Description: The cos function computes the cosine of x (measured in radians).  A large magnitude argument may yield a result with little or no significance. 

Returns: The cos function returns the cosine value. 

See Also: acos, sin, tan 

Example: 
#include <math.h> 
void main() 
 { 
  double value; 
  value = cos( 3.1415278 ); 
 } 

Classification: ANSI 

Systems: All


### cosh

Synopsis: 
#include <math.h> 
double cosh( double x ); 

Description: The cosh function computes the hyperbolic cosine of x.  A range error occurs if the magnitude of x is too large. 

Returns: The cosh function returns the hyperbolic cosine value.  When the argument is outside the permissible range, the  matherr function is called.  Unless the default  matherr function is replaced, it will set the global variable  errno to  ERANGE, and print a "RANGE error" diagnostic message using the  stderr stream. 

See Also: sinh, tanh, matherr 

Example: 
#include <stdio.h> 
#include <math.h> 
void main() 
 { 
  printf( "%f\n", cosh(.5) ); 
 } 
produces the following: 
1.127626 

Classification: ANSI 

Systems: All


### cprintf

Synopsis: 
#include <conio.h> 
int cprintf( const char *format, ... ); 

Description: The cprintf function writes output directly to the console under control of the argument format.  The  putch function is used to output characters to the console.  The format string is described under the description of the  printf function. 

Returns: The cprintf function returns the number of characters written. 

See Also: _bprintf, fprintf, printf, sprintf, _vbprintf, vcprintf, vfprintf, vprintf, vsprintf 

Example: 
#include <conio.h> 
void main() 
 { 
  char *weekday, *month; 
  int day, year; 
  weekday = "Saturday"; 
  month = "April"; 
  day = 18; 
  year = 1987; 
  cprintf( "%s, %s %d, %d\n", 
     weekday, month, day, year ); 
 } 
produces the following: 
Saturday, April 18, 1987 

Classification: WATCOM 

Systems: All


### cputs

Synopsis: 
#include <conio.h> 
int cputs( const char *buf ); 

Description: The cputs function writes the character string pointed to by buf directly to the console using the  putch function.  Unlike the  puts function, the carriage-return and line-feed characters are not appended to the string.  The terminating null character is not written. 

Returns: The cputs function returns a non-zero value if an error occurs; otherwise, it returns zero.  When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

See Also: fputs, putch, puts 

Example: 
#include <conio.h> 
void main() 
 { 
  char buffer[82]; 
  buffer[0] = 80; 
  cgets( buffer ); 
  cputs( &buffer[2] ); 
  putch( '\r' ); 
  putch( '\n' ); 
 } 

Classification: WATCOM 

Systems: All


### creat

Synopsis: 
#include <sys\types.h> 
#include <sys\stat.h> 
#include <io.h> 
int creat( const char *path, int mode ); 

Description: The creat function creates (and opens) a file at the operating system level.  It is equivalent to: 
    
    open( path, O_WRONLY | O_CREAT | O_TRUNC, mode ); 
The name of the file to be created is given by path.  When the file exists (it must be writeable), it is truncated to contain no data and the preceding mode setting is unchanged. 
When the file does not exist, it is created with access permissions given by the mode argument.  The access permissions for the file or directory are specified as a combination of bits (defined in the <sys\stat.h> header file). 
The following bits define permissions for the owner. 

S_IRWXU Read, write, execute/search 

S_IRUSR Read permission 

S_IWUSR Write permission 

S_IXUSR Execute/search permission 
The following bits define permissions for the group. 

S_IRWXG Read, write, execute/search 

S_IRGRP Read permission 

S_IWGRP Write permission 

S_IXGRP Execute/search permission 
The following bits define permissions for others. 

S_IRWXO Read, write, execute/search 

S_IROTH Read permission 

S_IWOTH Write permission 

S_IXOTH Execute/search permission 
The following bits define miscellaneous permissions used by other implementations. 

S_IREAD is equivalent to S_IRUSR (read permission) 

S_IWRITE is equivalent to S_IWUSR (write permission) 

S_IEXEC is equivalent to S_IXUSR (execute/search permission) 
All files are readable with DOS; however, it is a good idea to set S_IREAD when read permission is intended for the file. 

Returns: If successful, creat returns a handle for the file.  When an error occurs while opening the file, -1 is returned, and  errno is set to indicate the error. 

Errors: When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

EACCES Access denied because path specifies a directory or a volume ID, or a read-only file. 

EMFILE No more handles available (too many open files). 

ENOENT The specified path does not exist or path is an empty string. 

See Also: chsize, close, dup, dup2, eof, exec Functions, filelength, fileno, fstat, isatty, lseek, open, read, setmode, sopen, stat, tell, write, umask 

Example: 
#include <sys\types.h> 
#include <sys\stat.h> 
#include <io.h> 
void main() 
 { 
  int handle; 
  handle = creat( "file", S_IWRITE | S_IREAD ); 
  if( handle != -1 ) { 
   /* process file */ 
   close( handle ); 
  } 
 } 

Classification: POSIX 1003.1 

Systems: All


### cscanf

Synopsis: 
#include <conio.h> 
int cscanf( const char *format, ... ); 

Description: The cscanf function scans input from the console under control of the argument format.  Following the format string is a list of addresses to receive values.  The cscanf function uses the function  getche to read characters from the console.  The format string is described under the description of the  scanf function. 

Returns: The cscanf function returns  EOF when the scanning is terminated by reaching the end of the input stream.  Otherwise, the number of input arguments for which values were successfully scanned and stored is returned.  When a file input error occurs, the  errno global variable may be set. 

See Also: fscanf, scanf, sscanf, vcscanf, vfscanf, vscanf, vsscanf 

Example: 
To scan a date in the form "Saturday April 18 1987": 
#include <conio.h> 
void main() 
 { 
  int day, year; 
  char weekday[10], month[12]; 
  cscanf( "%s %s %d %d", 
      weekday, month, &day, &year ); 
  cprintf( "\n%s, %s %d, %d\n", 
      weekday, month, day, year ); 
 } 

Classification: WATCOM 

Systems: All


### ctime Functions

Synopsis: 
#include <time.h> 
char * ctime( const time_t *timer ); 
char *_ctime( const time_t *timer, char *buf ); 

Description: The ctime functions convert the calendar time pointed to by timer to local time in the form of a string.  The  ctime function is equivalent to 
    
   asctime( localtime( timer ) ) 
The ctime functions convert the time into a string containing exactly 26 characters.  This string has the form shown in the following example: 
    
   Sat Mar 21 15:58:27 1987\n\0 
All fields have a constant width.  The new-line character '\n' and the null character '\0' occupy the last two positions of the string. 
The ANSI function  ctime places the result string in a static buffer that is re-used each time  ctime or  asctime is called.  The non-ANSI function  _ctime places the result string in the buffer pointed to by buf. 
Whenever the ctime functions are called, the  tzset function is also called. 
The calendar time is usually obtained by using the  time function.  That time is Coordinated Universal Time (UTC) (formerly known as Greenwich Mean Time (GMT)). 
The time set on the computer with the DOS time command and the DOS date command reflects the local time.  The environment variable TZ is used to establish the time zone to which this local time applies.  See the section The TZ Environment Variable for a discussion of how to set the time zone. 

Returns: The ctime functions return the pointer to the string containing the local time. 

See Also: asctime, clock, difftime, gmtime, localtime, mktime, strftime, time, tzset 

Example: 
#include <stdio.h> 
#include <time.h> 
void main() 
 { 
  time_t time_of_day; 
  auto char buf[26]; 
  time_of_day = time( NULL ); 
  printf( "It is now: %s", _ctime( &time_of_day, buf ) ); 
 } 
produces the following: 
It is now: Fri Dec 25 15:58:42 1987 

Classification: ANSI 
_ctime is not ANSI 

Systems:  ctime - All 
_ctime - All


### cwait

Synopsis: 
#include <process.h> 
int cwait( int *status, int process_id, int action ); 

Description: The cwait function suspends the calling process until the specified child process terminates. 
If status is not NULL, it points to a word that will be filled in with the termination status word and return code of the terminated child process. 
If the child process terminated normally, then the low order byte of the status word will be set to 0, and the high order byte will contain the low order byte of the return code that the child process passed to the  DOSEXIT function.  The  DOSEXIT function is called whenever  main returns, or  exit or  _exit are explicity called. 
If the child process did not terminate normally, then the high order byte of the status word will be set to 0, and the low order byte will contain one of the following values: 

1 Hard-error abort 

2 Trap operation 

3 SIGTERM signal not intercepted 
The process_id argument specifies which child process to wait for.  This value is returned by the call to the  spawn function that started the child process. 
The action argument specifies when the parent process resumes execution.  The possible values are: 

WAIT_CHILD Wait until the specified child process has ended. 

WAIT_GRANDCHILD Wait until the specified child process and all of the child processes of that child process have ended. 

Returns: The cwait function returns the child's process id if the child process terminated normally.  Otherwise, cwait returns -1 and sets  errno to one of the following values: 

EINVAL Invalid action code 

ECHILD Invalid process id, or the child does not exist. 

EINTR The child process terminated abnormally. 

See Also: exit, _exit, spawn Functions, wait 

Example: 
#include <stdio.h> 
#include <process.h> 
void main() 
 { 
   int  process_id; 
   int  status; 
   process_id = spawnl( P_NOWAIT, "child.exe", 
        "child", "parm", NULL ); 
   cwait( &status, process_id, WAIT_CHILD ); 
 } 

Classification: OS/2 

Systems: OS/2 1.x(all), OS/2 2.x


### delay

Synopsis: 
#include <i86.h> 
void delay( unsigned milliseconds ); 

Description: The delay function suspends execution by the specified number of milliseconds. 

Returns: The delay function has no return value. 

See Also: sleep 

Example: 
#include <i86.h> 
void main() 
 { 
  sound( 200 ); 
  delay( 500 );  /* delay for 1/2 second */ 
  nosound(); 
 } 

Classification: WATCOM 

Systems: All


### difftime

Synopsis: 
#include <time.h> 
double difftime( time_t time1, time_t time0 ); 

Description: The difftime function calculates the difference between the two calendar times: 
    
     time1 - time0 

Returns: The difftime function returns the difference between the two times in seconds as a double. 

See Also: asctime, clock, ctime, gmtime, localtime, mktime, strftime, time, tzset 

Example: 
#include <stdio.h> 
#include <time.h> 
void compute( void ); 
void main() 
 { 
  time_t start_time, end_time; 
  start_time = time( NULL ); 
  compute(); 
  end_time = time( NULL ); 
  printf( "Elapsed time: %f seconds\n", 
    difftime( end_time, start_time ) ); 
 } 
void compute( void ) 
 { 
  int i, j; 
  for( i = 1; i <= 20; i++ ) { 
   for( j = 1; j <= 20; j++ ) 
    printf( "%3d ", i * j ); 
   printf( "\n" ); 
  } 
 } 

Classification: ANSI 

Systems: All


### _disable

Synopsis: 
#include <i86.h> 
void _disable( void ); 

Description: The _disable function causes interrupts to become disabled. 
The _disable function would be used in conjunction with the  _enable function to make sure that a sequence of instructions are executed without any intervening interrupts occurring. 

Returns: The _disable function returns no value. 

See Also: _enable 

Example: 
#include <stdio.h> 
#include <stdlib.h> 
#include <i86.h> 
struct list_entry { 
  struct list_entry *next; 
  int   data; 
}; 
volatile struct list_entry *ListHead = NULL; 
volatile struct list_entry *ListTail = NULL; 
void insert( struct list_entry *new_entry ) 
 { 
  /* insert new_entry at end of linked list */ 
  new_entry->next = NULL; 
  _disable();    /* disable interrupts */ 
  if( ListTail == NULL ) { 
   ListHead = new_entry; 
  } else { 
   ListTail->next = new_entry; 
  } 
  ListTail = new_entry; 
  _enable();     /* enable interrupts now */ 
 } 
void main() 
 { 
  struct list_entry *p; 
  int i; 
  for( i = 1; i <= 10; i++ ) { 
   p = (struct list_entry *) 
     malloc( sizeof( struct list_entry ) ); 
   if( p == NULL ) break; 
   p->data = i; 
   insert( p ); 
  } 
 } 

Classification: Intel 

Systems: All


### _displaycursor

Synopsis: 
#include <graph.h> 
short _FAR _displaycursor( short mode ); 

Description: The _displaycursor function is used to establish whether the text cursor is to be displayed when graphics functions complete.  On entry to a graphics function, the text cursor is turned off.  When the function completes, the mode setting determines whether the cursor is turned back on.  The mode argument can have one of the following values: 

_GCURSORON the cursor will be displayed 

_GCURSOROFF the cursor will not be displayed 

Returns: The _displaycursor function returns the previous setting for mode. 

See Also: _gettextcursor, _settextcursor 

Example: 
#include <stdio.h> 
#include <graph.h> 
main() 
{ 
  char buf[ 80 ]; 
  _setvideomode( _TEXTC80 ); 
  _settextposition( 2, 1 ); 
  _displaycursor( _GCURSORON ); 
  _outtext( "Cursor ON\n\nEnter your name >" ); 
  gets( buf ); 
  _displaycursor( _GCURSOROFF ); 
  _settextposition( 6, 1 ); 
  _outtext( "Cursor OFF\n\nEnter your name >" ); 
  gets( buf ); 
  _setvideomode( _DEFAULTMODE ); 
} 

Classification: PC Graphics 

Systems: DOS, QNX


### div

Synopsis: 
#include <stdlib.h> 
div_t div( int numer, int denom ); 
typedef struct { 
  int quot;   /* quotient */ 
  int rem;    /* remainder */ 
} div_t; 

Description: The div function calculates the quotient and remainder of the division of the numerator numer by the denominator denom. 

Returns: The div function returns a structure of type  div_t which contains the fields  quot and  rem. 

See Also: ldiv 

Example: 
#include <stdio.h> 
#include <stdlib.h> 
void print_time( int seconds ) 
 { 
   auto div_t min_sec; 
   min_sec = div( seconds, 60 ); 
   printf( "It took %d minutes and %d seconds\n", 
       min_sec.quot, min_sec.rem ); 
 } 
void main() 
 { 
  print_time( 130 ); 
 } 
produces the following: 
It took 2 minutes and 10 seconds 

Classification: ANSI 

Systems: All


### _dos_allocmem

Synopsis: 
#include <dos.h> 
unsigned _dos_allocmem( unsigned size, 
            unsigned short *segment); 

Description: The _dos_allocmem function uses system call 0x48 to allocate size paragraphs directly from DOS.  The size of a paragraph is 16 bytes.  The allocated memory is always paragraph aligned.  The segment descriptor for the allocated memory is returned in the word pointed to by segment.  If the allocation request fails, the maximum number of paragraphs that can be allocated is returned in this word instead. 

Returns: The _dos_allocmem function returns zero if successful.  Otherwise, it returns an MS-DOS error code and sets  errno to  ENOMEM indicating insufficient memory or corrupted memory. 

See Also: alloca, calloc, _dos_freemem, _dos_setblock, halloc, malloc 

Example: 
#include <stdio.h> 
#include <dos.h> 
void main() 
 { 
  unsigned short segment; 
  /* Try to allocate 100 paragraphs, then free them */ 
  if( _dos_allocmem( 100, &segment ) != 0 ) { 
   printf( "_dos_allocmem failed\n" ); 
   printf( "Only %u paragraphs available\n", 
        segment ); 
  } else { 
   printf( "_dos_allocmem succeeded\n" ); 
   if( _dos_freemem( segment ) != 0 ) { 
    printf( "_dos_freemem failed\n" ); 
   } else { 
    printf( "_dos_freemem succeeded\n" ); 
   } 
  } 
 } 

Classification: DOS 

Systems: DOS, OS/2 1.x(all), OS/2 2.x, NT, DOS/PM


### _dos_close

Synopsis: 
#include <dos.h> 
unsigned _dos_close( int handle ); 

Description: The _dos_close function uses system call 0x3E to close the file indicated by handle.  The value for handle is the one returned by a function call that created or last opened the file. 

Returns: The _dos_close function returns zero if successful.  Otherwise, it returns an MS-DOS error code and sets  errno to  EBADF indicating an invalid file handle. 

See Also: creat, _dos_creat, _dos_creatnew, _dos_open, dup, fclose, open 

Example: 
#include <stdio.h> 
#include <dos.h> 
#include <fcntl.h> 
void main() 
 { 
  int handle; 
  /* Try to open "stdio.h" and then close it */ 
  if( _dos_open( "stdio.h", O_RDONLY, &handle ) != 0 ){ 
   printf( "Unable to open file\n" ); 
  } else { 
   printf( "Open succeeded\n" ); 
   if( _dos_close( handle ) != 0 ) { 
    printf( "Close failed\n" ); 
   } else { 
    printf( "Close succeeded\n" ); 
   } 
  } 
 } 

Classification: DOS 

Systems: DOS, Win, OS/2 1.x(all), OS/2 2.x, NT, DOS/PM


### _dos_commit

Synopsis: 
#include <dos.h> 
int _dos_commit( int handle ); 

Description: The _dos_commit function uses system call 0x68 to flush to disk the DOS buffers associated with the file indicated by handle.  It also forces an update on the corresponding disk directory and the file allocation table. 

Returns: The _dos_commit function returns zero if successful.  Otherwise, it returns an MS-DOS error code and sets  errno to  EBADF indicating an invalid file handle. 

See Also: _dos_close, _dos_creat, _dos_open, _dos_write 

Example: 
#include <stdio.h> 
#include <dos.h> 
#include <fcntl.h> 
void main() 
 { 
  int handle; 
  if( _dos_open( "file", O_RDONLY, handle ) != 0 ) { 
    printf( "Unable to open file\n" ); 
  } else { 
    if( _dos_commit( handle ) == 0 ) { 
      printf( "Commit succeeded.\n" ); 
    } 
    _dos_close( handle ); 
  } 
 } 
produces the following: 
Commit succeeded. 

Classification: DOS 

Systems: DOS, Win, OS/2 1.x(all), OS/2 2.x, NT, DOS/PM


### _dos_creat

Synopsis: 
#include <dos.h> 
unsigned _dos_creat( char *path, 
           unsigned attribute, 
           int *handle ); 

Description: The _dos_creat function uses system call 0x3C to create a new file named path, with the access attributes specified by attribute.  The handle for the new file is returned in the word pointed to by handle.  If the file already exists, the contents will be erased, and the attributes of the file will remain unchanged.  The possible values for attribute are: 

_A_NORMAL Indicates a normal file.  File can be read or written without any restrictions. 

_A_RDONLY Indicates a read-only file.  File cannot be opened for "write". 

_A_HIDDEN Indicates a hidden file.  This file will not show up in a normal directory search. 

_A_SYSTEM Indicates a system file.  This file will not show up in a normal directory search. 

Returns: The _dos_creat function returns zero if successful.  Otherwise, it returns an MS-DOS error code and sets  errno to one of the following values: 

EACCES Access denied because the directory is full, or the file exists and cannot be overwritten. 

EMFILE No more handles available, (too many open files) 

ENOENT Path or file not found 

See Also: creat, _dos_creatnew, _dos_open, open 

Example: 
#include <stdio.h> 
#include <dos.h> 
void main() 
 { 
  int handle; 
  if( _dos_creat( "file", _A_NORMAL, &handle ) != 0 ){ 
   printf( "Unable to create file\n" ); 
  } else { 
   printf( "Create succeeded\n" ); 
   _dos_close( handle ); 
  } 
 } 

Classification: DOS 

Systems: DOS, Win, OS/2 1.x(all), OS/2 2.x, NT, DOS/PM


### _dos_creatnew

Synopsis: 
#include <dos.h> 
unsigned _dos_creatnew( char *path, 
            unsigned attribute, 
            int *handle ); 

Description: The _dos_creatnew function uses system call 0x5B to create a new file named path, with the access attributes specified by attribute.  The handle for the new file is returned in the word pointed to by handle.  If the file already exists, the create will fail.  The possible values for attribute are: 

_A_NORMAL Indicates a normal file.  File can be read or written without any restrictions. 

_A_RDONLY Indicates a read-only file.  File cannot be opened for "write". 

_A_HIDDEN Indicates a hidden file.  This file will not show up in a normal directory search. 

_A_SYSTEM Indicates a system file.  This file will not show up in a normal directory search. 

Returns: The _dos_creatnew function returns zero if successful.  Otherwise, it returns an MS-DOS error code and sets  errno to one of the following values: 

EACCES Access denied because the directory is full, or the file exists and cannot be overwritten. 

EEXIST File already exists 

EMFILE No more handles available, (too many open files) 

ENOENT Path or file not found 

See Also: creat, _dos_creat, _dos_open, open 

Example: 
#include <stdio.h> 
#include <dos.h> 
void main() 
 { 
  int handle1, handle2; 
  if( _dos_creat( "file", _A_NORMAL, &handle1 ) ){ 
   printf( "Unable to create file\n" ); 
  } else { 
   printf( "Create succeeded\n" ); 
   if( _dos_creatnew( "file", _A_NORMAL, &handle2 ) ){ 
    printf( "Unable to create new file\n" ); 
   } 
   _dos_close( handle1 ); 
  } 
 } 

Classification: DOS 

Systems: DOS, Win, OS/2 1.x(all), OS/2 2.x, NT, DOS/PM


### dosexterr

Synopsis: 
#include <dos.h> 
int dosexterr( struct DOSERROR *err_info ); 
struct _DOSERROR { 
    int exterror;  /* contents of AX register */ 
    char errclass;  /* contents of BH register */ 
    char action;   /* contents of BL register */ 
    char locus;   /* contents of CH register */ 
}; 

Description: The dosexterr function extracts extended error information following a failed DOS function.  This information is placed in the structure located by err_info.  This function is only useful with DOS version 3.0 or later. 
You should consult the technical documentation for the DOS system on your computer for an interpretation of the error information. 

Returns: The function returns an unpredictable result when the preceding DOS call did not result in an error.  Otherwise, the function returns the number of the extended error. 

See Also: perror 

Example: 
#include <stdio.h> 
#include <dos.h> 
#include <fcntl.h> 
struct _DOSERROR dos_err; 
void main() 
 { 
  int handle; 
  /* Try to open "stdio.h" and then close it */ 
  if( _dos_open( "stdio.h", O_RDONLY, &handle ) != 0 ){ 
   dosexterr( &dos_err ); 
   printf( "Unable to open file\n" ); 
   printf( "exterror (AX) = %d\n", dos_err.exterror ); 
   printf( "errclass (BH) = %d\n", dos_err.errclass ); 
   printf( "action  (BL) = %d\n", dos_err.action ); 
   printf( "locus   (CH) = %d\n", dos_err.locus ); 
  } else { 
   printf( "Open succeeded\n" ); 
   if( _dos_close( handle ) != 0 ) { 
    printf( "Close failed\n" ); 
   } else { 
    printf( "Close succeeded\n" ); 
   } 
  } 
 } 
produces the following: 
Unable to open file 
exterror (AX) = 2 
errclass (BH) = 8 
action  (BL) = 3 
locus   (CH) = 2 

Classification: DOS 

Systems: DOS, Win, DOS/PM


### _dos_find Functions

Synopsis: 
#include <dos.h> 
unsigned _dos_findfirst( char *path, 
             unsigned attributes, 
             struct find_t *buffer ); 
unsigned _dos_findnext(  struct find_t *buffer ); 
unsigned _dos_findclose( struct find_t *buffer ); 
struct find_t { 
 char reserved[21];    /* reserved for use by DOS  */ 
 char attrib;       /* attribute byte for file  */ 
 unsigned short wr_time; /* time of last write to file*/ 
 unsigned short wr_date; /* date of last write to file*/ 
 unsigned long  size;   /* length of file in bytes  */ 
#if defined(__OS2__) || defined(__NT__) 
 char name[256];     /* null-terminated filename  */ 
#else 
 char name[13];      /* null-terminated filename  */ 
#endif 
}; 

Description: The  _dos_findfirst function uses system call 0x4E to return information on the first file whose name and attributes match the path and attributes arguments.  The information is returned in a  find_t structure pointed to by buffer.  The path argument may contain wildcard characters ('?' and '*').  The attributes argument may be any combination of the following constants: 

_A_NORMAL Indicates a normal file.  File can be read or written without any restrictions. 

_A_RDONLY Indicates a read-only file.  File cannot be opened for "write". 

_A_HIDDEN Indicates a hidden file.  This file will not show up in a normal directory search. 

_A_SYSTEM Indicates a system file.  This file will not show up in a normal directory search. 

_A_VOLID Indicates a volume-ID. 

_A_SUBDIR Indicates a sub-directory. 

_A_ARCH This is the archive flag.  It is set whenever the file is modified, and is cleared by the MS-DOS BACKUP command and other backup utility programs. 
The attributes argument is interpreted by DOS as follows: 

 1.If  _A_NORMAL is specified, then normal files are included in the search. 

 2.If any of  _A_HIDDEN,  _A_SYSTEM,  _A_SUBDIR are specified, then normal files and the specified type of files are included in the search. 

 3.If  _A_VOLID is specified, then only volume-ID's are included in the search. 

 4. _A_RDONLY and  _A_ARCH are ignored by this function. 
The  _dos_findnext function uses system call 0x4F to return information on the next file whose name and attributes match the pattern supplied to the  _dos_findfirst function. 
On some systems (e.g.  OS/2), you must call  _dos_findclose to indicate that you are done matching files.  This function deallocates any resources that were allocated by the  _dos_findfirst function. 

Returns: The  _dos_find functions return zero if successful.  Otherwise, the  _dos_findfirst and  _dos_findnext functions return an MS-DOS error code and sets  errno to  ENOENT indicating that no more files matched the path and attributes arguments. 

See Also: opendir, readdir, closedir 

Example: 
#include <stdio.h> 
#include <dos.h> 
void main() 
 { 
  struct find_t  fileinfo; 
  unsigned rc;     /* return code */ 
  /* Display name and size of "*.c" files */ 
  rc = _dos_findfirst( "*.c", _A_NORMAL, &fileinfo ); 
  while( rc == 0 ) { 
   printf( "%14s %10ld\n", fileinfo.name, 
               fileinfo.size ); 
   rc = _dos_findnext( &fileinfo ); 
  } 
  #if defined(__OS2__) 
  _dos_findclose( &fileinfo ); 
  #endif 
 } 

Classification: DOS 

Systems:  _dos_findclose - DOS, Win, OS/2 1.x(all), OS/2 2.x, NT, DOS/PM 
_dos_findfirst - DOS, Win, OS/2 1.x(all), OS/2 2.x, NT, DOS/PM 
_dos_findnext - DOS, Win, OS/2 1.x(all), OS/2 2.x, NT, DOS/PM


### _dos_freemem

Synopsis: 
#include <dos.h> 
unsigned _dos_freemem( unsigned segment ); 

Description: The _dos_freemem function uses system call 0x49 to release memory that was previously allocated by  _dos_allocmem.  The value contained in segment is the one returned by a previous call to  _dos_allocmem. 

Returns: The _dos_freemem function returns zero if successful.  Otherwise, it returns an MS-DOS error code and sets  errno to  ENOMEM indicating a bad segment value or DOS memory has been corrupted. 

See Also: _dos_allocmem, _dos_setblock, free, hfree 

Example: 
#include <stdio.h> 
#include <dos.h> 
void main() 
 { 
  unsigned short segment; 
  /* Try to allocate 100 paragraphs, then free them */ 
  if( _dos_allocmem( 100, &segment ) != 0 ) { 
   printf( "_dos_allocmem failed\n" ); 
   printf( "Only %u paragraphs available\n", 
        segment ); 
  } else { 
   printf( "_dos_allocmem succeeded\n" ); 
   if( _dos_freemem( segment ) != 0 ) { 
    printf( "_dos_freemem failed\n" ); 
   } else { 
    printf( "_dos_freemem succeeded\n" ); 
   } 
  } 
 } 

Classification: DOS 

Systems: DOS, OS/2 1.x(all), OS/2 2.x, NT, DOS/PM


### _dos_getdate

Synopsis: 
#include <dos.h> 
void _dos_getdate( struct dosdate_t *date ); 
struct dosdate_t { 
    unsigned char day;    /* 1-31 */ 
    unsigned char month;   /* 1-12 */ 
    unsigned short year;   /* 1980-2099 */ 
    unsigned char dayofweek;/* 0-6 (0=Sunday) */ 
}; 

Description: The _dos_getdate function uses system call 0x2A to get the current system date.  The date information is returned in a  dosdate_t structure pointed to by date. 

Returns: The _dos_getdate function has no return value. 

See Also: _dos_gettime, _dos_setdate, _dos_settime, gmtime, localtime, mktime, time 

Example: 
#include <stdio.h> 
#include <dos.h> 
void main() 
 { 
  struct dosdate_t date; 
  struct dostime_t time; 
  /* Get and display the current date and time */ 
  _dos_getdate( &date ); 
  _dos_gettime( &time ); 
  printf( "The date (MM-DD-YYYY) is: %d-%d-%d\n", 
         date.month, date.day, date.year ); 
  printf( "The time (HH:MM:SS) is: %.2d:%.2d:%.2d\n", 
         time.hour, time.minute, time.second ); 
 } 
produces the following: 
The date (MM-DD-YYYY) is: 12-25-1989 
The time (HH:MM:SS) is: 14:23:57 

Classification: DOS 

Systems: DOS, Win, OS/2 1.x(all), OS/2 2.x, NT, DOS/PM


### _dos_getdiskfree

Synopsis: 
#include <dos.h> 
unsigned _dos_getdiskfree( unsigned drive, 
            struct diskfree_t *diskspace ); 
struct diskfree_t { 
    unsigned short total_clusters; 
    unsigned short avail_clusters; 
    unsigned short sectors_per_cluster; 
    unsigned short bytes_per_sector; 
}; 

Description: The _dos_getdiskfree function uses system call 0x36 to obtain useful information on the disk drive specified by drive.  Specify 0 for the default drive, 1 for drive A, 2 for drive B, etc.  The information about the drive is returned in the structure  diskfree_t pointed to by diskspace. 

Returns: The _dos_getdiskfree function returns zero if successful.  Otherwise, it returns a non-zero value and sets  errno to  EINVAL indicating an invalid drive was specified. 

See Also: _dos_getdrive, _dos_setdrive 

Example: 
#include <stdio.h> 
#include <dos.h> 
void main() 
 { 
  struct diskfree_t disk_data; 
  /* get information about drive 3 (the C drive) */ 
  if( _dos_getdiskfree( 3, &disk_data ) == 0 ) { 
   printf( "total clusters: %u\n", 
            disk_data.total_clusters ); 
   printf( "available clusters: %u\n", 
            disk_data.avail_clusters ); 
   printf( "sectors/cluster: %u\n", 
            disk_data.sectors_per_cluster ); 
   printf( "bytes per sector: %u\n", 
            disk_data.bytes_per_sector ); 
  } else { 
   printf( "Invalid drive specified\n" ); 
  } 
 } 
produces the following: 
total clusters: 16335 
available clusters: 510 
sectors/cluster: 4 
bytes per sector: 512 

Classification: DOS 

Systems: DOS, Win, NT, DOS/PM


### _dos_getdrive

Synopsis: 
#include <dos.h> 
void _dos_getdrive( unsigned *drive ); 

Description: The _dos_getdrive function uses system call 0x19 to get the current disk drive number.  The current disk drive number is returned in the word pointed to by drive.  A value of 1 is drive A, 2 is drive B, 3 is drive C, etc. 

Returns: The _dos_getdrive function has no return value. 

See Also: _dos_getdiskfree, _dos_setdrive 

Example: 
#include <stdio.h> 
#include <dos.h> 
void main() 
 { 
  unsigned drive; 
  _dos_getdrive( &drive ); 
  printf( "The current drive is %c\n", 
        'A' + drive - 1 ); 
 } 
produces the following: 
The current drive is C 

Classification: DOS 

Systems: DOS, Win, OS/2 1.x(all), OS/2 2.x, NT, DOS/PM


### _dos_getfileattr

Synopsis: 
#include <dos.h> 
unsigned _dos_getfileattr( char *path, 
              unsigned *attributes ); 

Description: The _dos_getfileattr function uses system call 0x43 to get the current attributes of the file or directory that path points to.  The possible attributes are: 

_A_NORMAL Indicates a normal file.  File can be read or written without any restrictions. 

_A_RDONLY Indicates a read-only file.  File cannot be opened for "write". 

_A_HIDDEN Indicates a hidden file.  This file will not show up in a normal directory search. 

_A_SYSTEM Indicates a system file.  This file will not show up in a normal directory search. 

_A_VOLID Indicates a volume-ID. 

_A_SUBDIR Indicates a sub-directory. 

_A_ARCH This is the archive flag.  It is set whenever the file is modified, and is cleared by the MS-DOS BACKUP command and other backup utility programs. 

Returns: The _dos_getfileattr function returns zero if successful.  Otherwise, it returns an MS-DOS error code and sets  errno to  ENOENT indicating that no file matched the path. 

See Also: _dos_setfileattr 

Example: 
#include <stdio.h> 
#include <dos.h> 
print_attribute() 
 { 
  unsigned attribute; 
  _dos_getfileattr( "file", &attribute ); 
  printf( "File attribute is %d\n", attribute ); 
  if( attribute & _A_RDONLY ) { 
    printf( "This is a read-only file.\n" ); 
  } else { 
    printf( "This is not a read-only file.\n" ); 
  } 
 } 
void main() 
 { 
  int    handle; 
  if( _dos_creat( "file", _A_RDONLY, &handle ) != 0 ) { 
   printf( "Error creating file\n" ); 
  } 
  print_attribute(); 
  _dos_setfileattr( "file", _A_NORMAL ); 
  print_attribute(); 
  _dos_close( handle ); 
 } 

Classification: DOS 

Systems: DOS, Win, OS/2 1.x(all), OS/2 2.x, NT, DOS/PM


### _dos_getftime

Synopsis: 
#include <dos.h> 
unsigned _dos_getftime( int handle, 
            unsigned short *date, 
            unsigned short *time ); 

Description: The _dos_getftime function uses system call 0x57 to get the date and time that the file associated with handle was last modified.  The date consists of the year, month and day packed into 16 bits as follows: 

bits 0-4 Day (1-31) 

bits 5-8 Month (1-12) 

bits 9-15 Year (0-119 representing 1980-2099) 
The time consists of the hour, minute and seconds/2 packed into 16 bits as follows: 

bits 0-4 Seconds/2 (0-29) 

bits 5-10 Minutes (0-59) 

bits 11-15 Hours (0-23) 

Returns: The _dos_getftime function returns zero if successful.  Otherwise, it returns an MS-DOS error code and sets  errno to one of the following values: 

EBADF Invalid file handle 

See Also: _dos_setftime 

Example: 
#include <stdio.h> 
#include <dos.h> 
#include <fcntl.h> 
#define YEAR(t)  (((t & 0xFE00) >> 9) + 1980) 
#define MONTH(t)  ((t & 0x01E0) >> 5) 
#define DAY(t)   (t & 0x001F) 
#define HOUR(t)  ((t & 0xF800) >> 11) 
#define MINUTE(t) ((t & 0x07E0) >> 5) 
#define SECOND(t) ((t & 0x001F) << 1) 
void main() 
 { 
  int    handle; 
  unsigned short date, time; 
  if( _dos_open( "file", O_RDONLY, &handle ) != 0 ) { 
   printf( "Unable to open file\n" ); 
  } else { 
   printf( "Open succeeded\n" ); 
   _dos_getftime( handle, &date, &time ); 
   printf( "The file was last modified on %d/%d/%d", 
       MONTH(date), DAY(date), YEAR(date) ); 
   printf( " at %.2d:%.2d:%.2d\n", 
       HOUR(time), MINUTE(time), SECOND(time) ); 
   _dos_close( handle ); 
  } 
 } 
produces the following: 
Open succeeded 
The file was last modified on 12/29/1989 at 14:32:46 

Classification: DOS 

Systems: DOS, Win, OS/2 1.x(all), OS/2 2.x, NT, DOS/PM


### _dos_gettime

Synopsis: 
#include <dos.h> 
void _dos_gettime( struct dostime_t *time ); 
struct dostime_t { 
    unsigned char hour;   /* 0-23 */ 
    unsigned char minute;  /* 0-59 */ 
    unsigned char second;  /* 0-59 */ 
    unsigned char hsecond;  /* 1/100 second; 0-99 */ 
}; 

Description: The _dos_gettime function uses system call 0x2C to get the current system time.  The time information is returned in a  dostime_t structure pointed to by time. 

Returns: The _dos_gettime function has no return value. 

See Also: _dos_getdate, _dos_setdate, _dos_settime, gmtime, localtime, mktime, time 

Example: 
#include <stdio.h> 
#include <dos.h> 
void main() 
 { 
  struct dosdate_t date; 
  struct dostime_t time; 
  /* Get and display the current date and time */ 
  _dos_getdate( &date ); 
  _dos_gettime( &time ); 
  printf( "The date (MM-DD-YYYY) is: %d-%d-%d\n", 
    date.month, date.day, date.year ); 
  printf( "The time (HH:MM:SS) is: %.2d:%.2d:%.2d\n", 
    time.hour, time.minute, time.second ); 
 } 
produces the following: 
The date (MM-DD-YYYY) is: 12-25-1989 
The time (HH:MM:SS) is: 14:23:57 

Classification: DOS 

Systems: DOS, Win, OS/2 1.x(all), OS/2 2.x, NT, DOS/PM


### _dos_getvect

Synopsis: 
#include <dos.h> 
void (__interrupt __far *_dos_getvect(unsigned intnum))(); 

Description: The _dos_getvect function gets the current value of interrupt vector number intnum. 

Returns: The function returns a far pointer to the current interrupt handler for interrupt number intnum. 

See Also: _chain_intr, _dos_keep, _dos_setvect 

Example: 
#include <stdio.h> 
#include <dos.h> 
volatile int clock_ticks; 
void (__interrupt __far *prev_int_1c)(); 
#define BLIP_COUNT  (5*18)  /* 5 seconds */ 
void __interrupt __far timer_rtn() 
 { 
  ++clock_ticks; 
  _chain_intr( prev_int_1c ); 
 } 
int delays = 0; 
int compile_a_line() 
 { 
  if( delays > 15 ) return( 0 ); 
  delay( 1000 );  /* delay for 1 second */ 
  printf( "Delayed for 1 second\n" ); 
  delays++; 
  return( 1 ); 
 } 
void main() 
 { 
  prev_int_1c = _dos_getvect( 0x1c ); 
  _dos_setvect( 0x1c, timer_rtn ); 
  while( compile_a_line() ) { 
    if( clock_ticks >= BLIP_COUNT ) { 
      putchar( '.' ); 
      clock_ticks -= BLIP_COUNT; 
    } 
  } 
  _dos_setvect( 0x1c, prev_int_1c ); 
 } 

Classification: WATCOM 

Systems: DOS, Win/16, DOS/PM


### _dos_keep

Synopsis: 
#include <dos.h> 
void _dos_keep( unsigned retcode, unsigned memsize ); 

Description: The _dos_keep function is used to install terminate-and-stay-resident programs ("TSR's") in memory.  The amount of memory kept for the program is memsize paragraphs (a paragraph is 16 bytes) from the Program Segment Prefix which is stored in the variable  _psp.  The value of retcode is returned to the parent process. 

Returns: The _dos_keep function does not return. 

See Also: _chain_intr, _dos_getvect, _dos_setvect 

Example: 
#include <dos.h> 
void permanent() 
 { 
  /* . */ 
  /* . */ 
  /* . */ 
 } 
void transient() 
 { 
  /* . */ 
  /* . */ 
  /* . */ 
 } 
void main() 
 { 
  /* initialize our TSR */ 
  transient(); 
  /* 
    now terminate and keep resident 
    the non-transient portion 
  */ 
  _dos_keep( 0, (FP_OFF( transient ) + 15) >> 4 ); 
 } 

Classification: DOS 

Systems: DOS


### _dos_open

Synopsis: 
#include <dos.h> 
#include <fcntl.h> 
#include <share.h> 
unsigned _dos_open( char *path, 
          unsigned mode, 
          int *handle ); 

Description: The _dos_open function uses system call 0x3D to open the file specified by path, which must be an existing file.  The mode argument specifies the file's access, sharing and inheritance permissions.  The access mode must be one of: 

O_RDONLY Read only 

O_WRONLY Write only 

O_RDWR Both read and write 
The sharing permissions, if specified, must be one of: 

SH_COMPAT Set compatibility mode. 

SH_DENYRW Prevent read or write access to the file. 

SH_DENYWR Prevent write access of the file. 

SH_DENYRD Prevent read access to the file. 

SH_DENYNO Permit both read and write access to the file. 
The inheritance permission, if specified, is: 

O_NOINHERIT File is not inherited by a child process 

Returns: The _dos_open function returns zero if successful.  Otherwise, it returns an MS-DOS error code and sets  errno to one of the following values: 

EACCES Access denied because path specifies a directory or a volume ID, or opening a read-only file for write access 

EINVAL A sharing mode was specified when file sharing is not installed, or access-mode value is invalid 

EMFILE No more handles available, (too many open files) 

ENOENT Path or file not found 

See Also: _dos_close, _dos_creat, _dos_creatnew, _dos_read, _dos_write, open 

Example: 
#include <stdio.h> 
#include <dos.h> 
#include <fcntl.h> 
#include <share.h> 
void main() 
 { 
  int handle; 
  if( _dos_open( "file", O_RDONLY, &handle ) != 0 ) { 
    printf( "Unable to open file\n" ); 
  } else { 
    printf( "Open succeeded\n" ); 
    _dos_close( handle ); 
  } 
 } 

Classification: DOS 

Systems: DOS, Win, OS/2 1.x(all), OS/2 2.x, NT, DOS/PM


### _dos_read

Synopsis: 
#include <dos.h> 
unsigned _dos_read( int handle, void __far *buffer, 
          unsigned count, unsigned *bytes ); 

Description: The _dos_read function uses system call 0x3F to read count bytes of data from the file specified by handle into the buffer pointed to by buffer.  The number of bytes successfully read will be stored in the unsigned integer pointed to by bytes. 

Returns: The _dos_read function returns zero if successful.  Otherwise, it returns an MS-DOS error code and sets  errno to one of the following values: 

EACCES Access denied because the file is not open for read access 

EBADF Invalid file handle 

See Also: _dos_close, _dos_open, _dos_write 

Example: 
#include <stdio.h> 
#include <dos.h> 
#include <fcntl.h> 
void main() 
 { 
  unsigned len_read; 
  int    handle; 
  auto char buffer[80]; 
  if( _dos_open( "file", O_RDONLY, &handle ) != 0 ) { 
   printf( "Unable to open file\n" ); 
  } else { 
   printf( "Open succeeded\n" ); 
   _dos_read( handle, buffer, 80, &len_read ); 
   _dos_close( handle ); 
  } 
 } 

Classification: DOS 

Systems: DOS, Win, OS/2 1.x(all), OS/2 2.x, NT, DOS/PM


### _dos_setblock

Synopsis: 
#include <dos.h> 
unsigned _dos_setblock( unsigned size, 
            unsigned short segment, 
            unsigned *maxsize ); 

Description: The _dos_setblock function uses system call 0x4A to change the size of segment, which was previously allocated by  _dos_allocmem, to size paragraphs.  If the request fails, the maximum number of paragraphs that this memory block can be changed to is returned in the word pointed to by maxsize. 

Returns: The _dos_setblock function returns zero if successful.  Otherwise, it returns an MS-DOS error code and sets  errno to  ENOMEM indicating a bad segment value, insufficient memory or corrupted memory. 

See Also: _dos_allocmem, _dos_freemem, realloc 

Example: 
#include <stdio.h> 
#include <dos.h> 
void main() 
 { 
  unsigned short segment; 
  unsigned maxsize; 
  /* Try to allocate 100 paragraphs, then free them */ 
  if( _dos_allocmem( 100, &segment ) != 0 ) { 
   printf( "_dos_allocmem failed\n" ); 
   printf( "Only %u paragraphs available\n",segment); 
  } else { 
   printf( "_dos_allocmem succeeded\n" ); 
   /* Try to increase it to 200 paragraphs */ 
   if( _dos_setblock( 200, segment, &maxsize ) != 0 ){ 
    printf( "Unable to increase the size\n" ); 
   } 
   if( _dos_freemem( segment ) != 0 ) { 
    printf( "_dos_freemem failed\n" ); 
   } 
  } 
 } 

Classification: DOS 

Systems: DOS, DOS/PM


### _dos_setdate

Synopsis: 
#include <dos.h> 
unsigned _dos_setdate( struct dosdate_t *date ); 
struct dosdate_t { 
    unsigned char day;    /* 1-31 */ 
    unsigned char month;   /* 1-12 */ 
    unsigned short year;   /* 1980-2099 */ 
    unsigned char dayofweek;/* 0-6 (0=Sunday) */ 
}; 

Description: The _dos_setdate function uses system call 0x2B to set the current system date.  The date information is passed in a  dosdate_t structure pointed to by date. 

Returns: The _dos_setdate function returns zero if successful.  Otherwise, it returns a non-zero value and sets  errno to  EINVAL indicating that an invalid date was given. 

See Also: _dos_getdate, _dos_gettime, _dos_settime, gmtime, localtime, mktime, time 

Example: 
#include <stdio.h> 
#include <dos.h> 
void main() 
 { 
  struct dosdate_t date; 
  struct dostime_t time; 
  /* Get and display the current date and time */ 
  _dos_getdate( &date ); 
  _dos_gettime( &time ); 
  printf( "The date (MM-DD-YYYY) is: %d-%d-%d\n", 
    date.month, date.day, date.year ); 
  printf( "The time (HH:MM:SS) is: %.2d:%.2d:%.2d\n", 
    time.hour, time.minute, time.second ); 
  /* Change it to the turn of the century */ 
  date.year = 1999; 
  date.month = 12; 
  date.day = 31; 
  time.hour = 23; 
  time.minute = 59; 
  _dos_setdate( &date ); 
  _dos_settime( &time ); 
  printf( "New date (MM-DD-YYYY) is: %d-%d-%d\n", 
    date.month, date.day, date.year ); 
  printf( "New time (HH:MM:SS) is: %.2d:%.2d:%.2d\n", 
    time.hour, time.minute, time.second ); 
 } 
produces the following: 
The date (MM-DD-YYYY) is: 12-25-1989 
The time (HH:MM:SS) is: 14:23:15 
New date (MM-DD-YYYY) is: 12-31-1999 
New time (HH:MM:SS) is: 23:59:16 

Classification: DOS 

Systems: DOS, Win, OS/2 1.x(all), OS/2 2.x, NT, DOS/PM


### _dos_setdrive

Synopsis: 
#include <dos.h> 
void _dos_setdrive( unsigned drive, unsigned *total ); 

Description: The _dos_setdrive function uses system call 0x0E to set the current default disk drive to be the drive specified by drive, where 1 = drive A, 2 = drive B, etc.  The total number of disk drives is returned in the word pointed to by total.  For DOS versions 3.0 or later, the minimum number of drives returned is 5. 

Returns: The _dos_setdrive function has no return value.  If an invalid drive number is specified, the function fails with no error indication.  You must use the  _dos_getdrive function to check that the desired drive has been set. 

See Also: _dos_getdiskfree, _dos_getdrive 

Example: 
#include <stdio.h> 
#include <dos.h> 
void main() 
 { 
  unsigned drive1, drive2, total; 
  _dos_getdrive( &drive1 ); 
  printf( "Current drive is %c\n", 'A' + drive1 - 1 ); 
  /* try to change to drive C */ 
  _dos_setdrive( 3, &total ); 
  _dos_getdrive( &drive2 ); 
  printf( "Current drive is %c\n", 'A' + drive2 - 1 ); 
  /* go back to original drive */ 
  _dos_setdrive( drive1, &total ); 
  _dos_getdrive( &drive1 ); 
  printf( "Current drive is %c\n", 'A' + drive1 - 1 ); 
  printf( "Total number of drives is %u\n", total ); 
 } 
produces the following: 
Current drive is D 
Current drive is C 
Total number of drives is 6 

Classification: DOS 

Systems: DOS, Win, OS/2 1.x(all), OS/2 2.x, NT, DOS/PM


### _dos_setfileattr

Synopsis: 
#include <dos.h> 
unsigned _dos_setfileattr( char *path, 
              unsigned attributes ); 

Description: The _dos_setfileattr function uses system call 0x43 to set the attributes of the file or directory that path points to.  The possible attributes are: 

_A_NORMAL Indicates a normal file.  File can be read or written without any restrictions. 

_A_RDONLY Indicates a read-only file.  File cannot be opened for "write". 

_A_HIDDEN Indicates a hidden file.  This file will not show up in a normal directory search. 

_A_SYSTEM Indicates a system file.  This file will not show up in a normal directory search. 

_A_VOLID Indicates a volume-ID. 

_A_SUBDIR Indicates a sub-directory. 

_A_ARCH This is the archive flag.  It is set whenever the file is modified, and is cleared by the MS-DOS BACKUP command and other backup utility programs. 

Returns: The _dos_setfileattr function returns zero if successful.  Otherwise, it returns an MS-DOS error code and sets  errno to one of the following: 

ENOENT No file or directory matched the specified path. 

EACCES Access denied; cannot change the volume ID or the subdirectory. 

See Also: _dos_getfileattr 

Example: 
#include <stdio.h> 
#include <dos.h> 
print_attribute() 
 { 
  unsigned attribute; 
  _dos_getfileattr( "file", &attribute ); 
  printf( "File attribute is %x\n", attribute ); 
  if( attribute & _A_RDONLY ) { 
    printf( "This is a read-only file\n" ); 
  } else { 
    printf( "This is not a read-only file\n" ); 
  } 
 } 
void main() 
 { 
  int    handle; 
  if( _dos_creat( "file", _A_RDONLY, &handle ) != 0 ){ 
   printf( "Error creating file\n" ); 
  } 
  print_attribute(); 
  _dos_setfileattr( "file", _A_NORMAL ); 
  print_attribute(); 
  _dos_close( handle ); 
 } 

Classification: DOS 

Systems: DOS, Win, OS/2 1.x(all), OS/2 2.x, NT, DOS/PM


### _dos_setftime

Synopsis: 
#include <dos.h> 
unsigned _dos_setftime( int handle, 
            unsigned short date, 
            unsigned short time ); 

Description: The _dos_setftime function uses system call 0x57 to set the date and time that the file associated with handle was last modified.  The date consists of the year, month and day packed into 16 bits as follows: 

bits 0-4 Day (1-31) 

bits 5-8 Month (1-12) 

bits 9-15 Year (0-119 representing 1980-2099) 
The time consists of the hour, minute and seconds/2 packed into 16 bits as follows: 

bits 0-4 Seconds/2 (0-29) 

bits 5-10 Minutes (0-59) 

bits 11-15 Hours (0-23) 

Returns: The _dos_setftime function returns zero if successful.  Otherwise, it returns an MS-DOS error code and sets  errno to one of the following values: 

EBADF Invalid file handle 

See Also: _dos_getftime 

Example: 
#include <stdio.h> 
#include <dos.h> 
#include <fcntl.h> 
#define YEAR(t)  (((t & 0xFE00) >> 9) + 1980) 
#define MONTH(t)  ((t & 0x01E0) >> 5) 
#define DAY(t)   (t & 0x001F) 
#define HOUR(t)  ((t & 0xF800) >> 11) 
#define MINUTE(t) ((t & 0x07E0) >> 5) 
#define SECOND(t) ((t & 0x001F) << 1) 
void main() 
 { 
  int    handle; 
  unsigned short date, time; 
  if( _dos_open( "file", O_RDONLY, &handle ) != 0 ) { 
   printf( "Unable to open file\n" ); 
  } else { 
   printf( "Open succeeded\n" ); 
   _dos_getftime( handle, &date, &time ); 
   printf( "The file was last modified on %d/%d/%d", 
       MONTH(date), DAY(date), YEAR(date) ); 
   printf( " at %.2d:%.2d:%.2d\n", 
       HOUR(time), MINUTE(time), SECOND(time) ); 
   /* set the time to 12 noon */ 
   time = (12 << 11) + (0 << 5) + 0; 
   _dos_setftime( handle, date, time ); 
   _dos_getftime( handle, &date, &time ); 
   printf( "The file was last modified on %d/%d/%d", 
       MONTH(date), DAY(date), YEAR(date) ); 
   printf( " at %.2d:%.2d:%.2d\n", 
       HOUR(time), MINUTE(time), SECOND(time) ); 
   _dos_close( handle ); 
  } 
 } 
produces the following: 
Open succeeded 
The file was last modified on 12/29/1989 at 14:32:46 
The file was last modified on 12/29/1989 at 12:00:00 

Classification: DOS 

Systems: DOS, Win, OS/2 1.x(all), OS/2 2.x, NT, DOS/PM


### _dos_settime

Synopsis: 
#include <dos.h> 
unsigned _dos_settime( struct dostime_t *time ); 
struct dostime_t { 
    unsigned char hour;   /* 0-23 */ 
    unsigned char minute;  /* 0-59 */ 
    unsigned char second;  /* 0-59 */ 
    unsigned char hsecond;  /* 1/100 second; 0-99 */ 
}; 

Description: The _dos_settime function uses system call 0x2D to set the current system time.  The time information is passed in a  dostime_t structure pointed to by time. 

Returns: The _dos_settime function returns zero if successful.  Otherwise, it returns a non-zero value and sets  errno to  EINVAL indicating that an invalid time was given. 

See Also: _dos_getdate, _dos_setdate, _dos_gettime, gmtime, localtime, mktime, time 

Example: 
#include <stdio.h> 
#include <dos.h> 
void main() 
 { 
  struct dosdate_t date; 
  struct dostime_t time; 
  /* Get and display the current date and time */ 
  _dos_getdate( &date ); 
  _dos_gettime( &time ); 
  printf( "The date (MM-DD-YYYY) is: %d-%d-%d\n", 
    date.month, date.day, date.year ); 
  printf( "The time (HH:MM:SS) is: %.2d:%.2d:%.2d\n", 
    time.hour, time.minute, time.second ); 
  /* Change it to the turn of the century */ 
  date.year = 1999; 
  date.month = 12; 
  date.day = 31; 
  time.hour = 23; 
  time.minute = 59; 
  _dos_setdate( &date ); 
  _dos_settime( &time ); 
  printf( "New date (MM-DD-YYYY) is: %d-%d-%d\n", 
         date.month, date.day, date.year ); 
  printf( "New time (HH:MM:SS) is: %.2d:%.2d:%.2d\n", 
         time.hour, time.minute, time.second ); 
 } 
produces the following: 
The date (MM-DD-YYYY) is: 12-25-1989 
The time (HH:MM:SS) is: 14:23:15 
New date (MM-DD-YYYY) is: 12-31-1999 
New time (HH:MM:SS) is: 23:59:16 

Classification: DOS 

Systems: DOS, Win, OS/2 1.x(all), OS/2 2.x, NT, DOS/PM


### _dos_setvect

Synopsis: 
#include <dos.h> 
void _dos_setvect( unsigned intnum, 
          void (__interrupt __far *handler)() ); 

Description: The _dos_setvect function sets interrupt vector number intnum to point to the interrupt handling function pointed to by handler. 

Returns: The function does not return a value. 

See Also: _chain_intr, _dos_getvect, _dos_keep 

Example: 
#include <stdio.h> 
#include <dos.h> 
volatile int clock_ticks; 
void (__interrupt __far *prev_int_1c)(); 
#define BLIP_COUNT  (5*18)  /* 5 seconds */ 
void __interrupt __far timer_rtn() 
 { 
  ++clock_ticks; 
  _chain_intr( prev_int_1c ); 
 } 
int delays = 0; 
void main() 
 { 
  prev_int_1c = _dos_getvect( 0x1c ); 
  _dos_setvect( 0x1c, timer_rtn ); 
  while( compile_a_line() ) { 
    if( clock_ticks >= BLIP_COUNT ) { 
      putchar( '.' ); 
      clock_ticks -= BLIP_COUNT; 
    } 
  } 
  _dos_setvect( 0x1c, prev_int_1c ); 
 } 
int compile_a_line() 
 { 
  if( delays > 15 ) return( 0 ); 
  delay( 1000 );  /* delay for 1 second */ 
  printf( "Delayed for 1 second\n" ); 
  delays++; 
  return( 1 ); 
 } 

Classification: WATCOM 

Systems: DOS, Win/16, DOS/PM


### _dos_write

Synopsis: 
#include <dos.h> 
unsigned _dos_write( int handle, void __far *buffer, 
           unsigned count, unsigned *bytes ); 

Description: The _dos_write function uses system call 0x40 to write count bytes of data from the buffer pointed to by buffer to the file specified by handle.  The number of bytes successfully written will be stored in the unsigned integer pointed to by bytes. 

Returns: The _dos_write function returns zero if successful.  Otherwise, it returns an MS-DOS error code and sets  errno to one of the following values: 

EACCES Access denied because the file is not open for write access 

EBADF Invalid file handle 

See Also: _dos_close, _dos_open, _dos_read 

Example: 
#include <stdio.h> 
#include <dos.h> 
#include <fcntl.h> 
char buffer[] = "This is a test for _dos_write."; 
void main() 
 { 
  unsigned len_written; 
  int    handle; 
  if( _dos_creat( "file", _A_NORMAL, &handle ) != 0 ) { 
   printf( "Unable to create file\n" ); 
  } else { 
   printf( "Create succeeded\n" ); 
   _dos_write( handle, buffer, sizeof(buffer), 
         &len_written ); 
   _dos_close( handle ); 
  } 
 } 

Classification: DOS 

Systems: DOS, Win, OS/2 1.x(all), OS/2 2.x, NT, DOS/PM


### dup

Synopsis: 
#include <io.h> 
int dup( int handle ); 

Description: The dup function duplicates the file handle given by the argument handle.  The new file handle refers to the same open file handle as the original file handle, and shares any locks.  The new file handle is identical to the original in that it references the same file or device, it has the same open mode (read and/or write) and it will have file position identical to the original.  Changing the position with one handle will result in a changed position in the other. 

Returns: If successful, the new file handle is returned to be used with the other functions which operate on the file.  Otherwise, -1 is returned and  errno is set to indicate the error. 

Errors: When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

EBADF The argument handle is not a valid open file handle. 

EMFILE The number of file handles would exceed {OPEN_MAX}. 

See Also: chsize, close, creat, dup2, eof, exec Functions, filelength, fileno, fstat, isatty, lseek, open, read, setmode, sopen, stat, tell, write, umask 

Example: 
#include <fcntl.h> 
#include <io.h> 
void main() 
 { 
  int handle, dup_handle; 
  handle = open( "file", 
        O_WRONLY | O_CREAT | O_TRUNC | O_TEXT, 
        S_IRUSR | S_IWUSR | S_IRGRP | S_IWGRP ); 
  if( handle != -1 ) { 
   dup_handle = dup( handle ); 
   if( dup_handle != -1 ) { 
    /* process file */ 
    close( dup_handle ); 
   } 
   close( handle ); 
  } 
 } 

Classification: POSIX 1003.1 

Systems: All


### dup2

Synopsis: 
#include <io.h> 
int dup2( int handle, int handle2 ); 

Description: The dup2 function duplicates the file handle given by the argument handle.  The new file handle is identical to the original in that it references the same file or device, it has the same open mode (read and/or write) and it will have identical file position to the original (changing the position with one handle will result in a changed position in the other). 
The number of the new handle is handle2.  If a file already is opened with this handle, the file is closed before the duplication is attempted. 

Returns: The dup2 function returns zero if successful.  Otherwise, -1 is returned and  errno is set to indicate the error. 

Errors: When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

EBADF The argument handle is not a valid open file handle or handle2 is out of range. 

EMFILE The number of file handles would exceed {OPEN_MAX}, or no file handles above handle2 are available. 

See Also: chsize, close, creat, dup, eof, exec Functions, filelength, fileno, fstat, isatty, lseek, open, read, setmode, sopen, stat, tell, write, umask 

Example: 
#include <fcntl.h> 
#include <io.h> 
void main() 
 { 
  int handle, dup_handle; 
  handle = open( "file", 
        O_WRONLY | O_CREAT | O_TRUNC | O_TEXT, 
        S_IRUSR | S_IWUSR | S_IRGRP | S_IWGRP ); 
  if( handle != -1 ) { 
   dup_handle = 4; 
   if( dup2( handle, dup_handle ) != -1 ) { 
    /* process file */ 
    close( dup_handle ); 
   } 
   close( handle ); 
  } 
 } 

Classification: POSIX 1003.1 

Systems: All


### _dwDeleteOnClose

Synopsis: 
#include <wdefwin.h> 
int _dwDeleteOnClose( int handle ); 

Description: The _dwDeleteOnClose function tells the console window that it should close itself when the corresponding file is closed.  The argument handle is the handle associated with the opened console. 
The _dwDeleteOnClose function is one of the support functions that can be called from an application using WATCOM's default windowing support. 

Returns: The _dwDeleteOnClose function returns 1 if it was successful and 0 if not. 

See Also: _dwSetAboutDlg, _dwSetAppTitle, _dwSetConTitle, _dwShutDown, _dwYield 

Example: 
#include <wdefwin.h> 
#include <stdio.h> 
void main() 
 { 
  FILE *sec; 
  _dwSetAboutDlg( "Hello World About Dialog", 
          "About Hello World\n" 
          "Copyright 1994 by WATCOM\n" ); 
  _dwSetAppTitle( "Hello World Application Title" ); 
  _dwSetConTitle( 0, "Hello World Console Title" ); 
  printf( "Hello World\n" ); 
  sec = fopen( "CON", "r+" ); 
  _dwSetConTitle( fileno( sec ), 
          "Hello World Second Console Title" ); 
  _dwDeleteOnClose( fileno( sec ) ); 
  fprintf( sec, "Hello to second console\n" ); 
  fprintf( sec, "Press Enter to close this console\n" ); 
  fflush( sec ); 
  fgetc( sec ); 
  fclose( sec ); 
 } 

Classification: WATCOM 

Systems: Win, OS/2 2.x, NT


### _dwSetAboutDlg

Synopsis: 
#include <wdefwin.h> 
int _dwSetAboutDlg( const char *title, const char *text ); 

Description: The _dwSetAboutDlg function sets the "About" dialog box of the default windowing system.  The argument title points to the string that will replace the current title.  If title is NULL then the title will not be replaced.  The argument text points to a string which will be placed in the "About" box.  To get multiple lines, embed a new line after each logical line in the string.  If text is NULL, then the current text in the "About" box will not be replaced. 
The _dwSetAboutDlg function is one of the support functions that can be called from an application using WATCOM's default windowing support. 

Returns: The _dwSetAboutDlg function returns 1 if it was successful and 0 if not. 

See Also: _dwDeleteOnClose, _dwSetAppTitle, _dwSetConTitle, _dwShutDown, _dwYield 

Example: 
#include <wdefwin.h> 
#include <stdio.h> 
void main() 
 { 
  FILE *sec; 
  _dwSetAboutDlg( "Hello World About Dialog", 
          "About Hello World\n" 
          "Copyright 1994 by WATCOM\n" ); 
  _dwSetAppTitle( "Hello World Application Title" ); 
  _dwSetConTitle( 0, "Hello World Console Title" ); 
  printf( "Hello World\n" ); 
  sec = fopen( "CON", "r+" ); 
  _dwSetConTitle( fileno( sec ), 
          "Hello World Second Console Title" ); 
  _dwDeleteOnClose( fileno( sec ) ); 
  fprintf( sec, "Hello to second console\n" ); 
  fprintf( sec, "Press Enter to close this console\n" ); 
  fflush( sec ); 
  fgetc( sec ); 
  fclose( sec ); 
 } 

Classification: WATCOM 

Systems: Win, OS/2 2.x, NT


### _dwSetAppTitle

Synopsis: 
#include <wdefwin.h> 
int _dwSetAppTitle( const char *title ); 

Description: The _dwSetAppTitle function sets the main window's title.  The argument title points to the string that will replace the current title. 
The _dwSetAppTitle function is one of the support functions that can be called from an application using WATCOM's default windowing support. 

Returns: The _dwSetAppTitle function returns 1 if it was successful and 0 if not. 

See Also: _dwDeleteOnClose, _dwSetAboutDlg, _dwSetConTitle, _dwShutDown, _dwYield 

Example: 
#include <wdefwin.h> 
#include <stdio.h> 
void main() 
 { 
  FILE *sec; 
  _dwSetAboutDlg( "Hello World About Dialog", 
          "About Hello World\n" 
          "Copyright 1994 by WATCOM\n" ); 
  _dwSetAppTitle( "Hello World Application Title" ); 
  _dwSetConTitle( 0, "Hello World Console Title" ); 
  printf( "Hello World\n" ); 
  sec = fopen( "CON", "r+" ); 
  _dwSetConTitle( fileno( sec ), 
          "Hello World Second Console Title" ); 
  _dwDeleteOnClose( fileno( sec ) ); 
  fprintf( sec, "Hello to second console\n" ); 
  fprintf( sec, "Press Enter to close this console\n" ); 
  fflush( sec ); 
  fgetc( sec ); 
  fclose( sec ); 
 } 

Classification: WATCOM 

Systems: Win, OS/2 2.x, NT


### _dwSetConTitle

Synopsis: 
#include <wdefwin.h> 
int _dwSetConTitle( int handle, const char *title ); 

Description: The _dwSetConTitle function sets the console window's title which corresponds to the handle passed to it.  The argument handle is the handle associated with the opened console.  The argument title points to the string that will replace the current title. 
The _dwSetConTitle function is one of the support functions that can be called from an application using WATCOM's default windowing support. 

Returns: The _dwSetConTitle function returns 1 if it was successful and 0 if not. 

See Also: _dwDeleteOnClose, _dwSetAboutDlg, _dwSetAppTitle, _dwShutDown, _dwYield 

Example: 
#include <wdefwin.h> 
#include <stdio.h> 
void main() 
 { 
  FILE *sec; 
  _dwSetAboutDlg( "Hello World About Dialog", 
          "About Hello World\n" 
          "Copyright 1994 by WATCOM\n" ); 
  _dwSetAppTitle( "Hello World Application Title" ); 
  _dwSetConTitle( 0, "Hello World Console Title" ); 
  printf( "Hello World\n" ); 
  sec = fopen( "CON", "r+" ); 
  _dwSetConTitle( fileno( sec ), 
          "Hello World Second Console Title" ); 
  _dwDeleteOnClose( fileno( sec ) ); 
  fprintf( sec, "Hello to second console\n" ); 
  fprintf( sec, "Press Enter to close this console\n" ); 
  fflush( sec ); 
  fgetc( sec ); 
  fclose( sec ); 
 } 

Classification: WATCOM 

Systems: Win, OS/2 2.x, NT


### _dwShutDown

Synopsis: 
#include <wdefwin.h> 
int _dwShutDown( void ); 

Description: The _dwShutDown function shuts down the default windowing I/O system.  The application will continue to execute but no windows will be available for output.  Care should be exercised when using this function since any subsequent output may cause unpredictable results. 
When the application terminates, it will not be necessary to manually close the main window. 
The _dwShutDown function is one of the support functions that can be called from an application using WATCOM's default windowing support. 

Returns: The _dwShutDown function returns 1 if it was successful and 0 if not. 

See Also: _dwDeleteOnClose, _dwSetAboutDlg, _dwSetAppTitle, _dwSetConTitle, _dwYield 

Example: 
#include <wdefwin.h> 
#include <stdio.h> 
void main() 
 { 
  FILE *sec; 
  _dwSetAboutDlg( "Hello World About Dialog", 
          "About Hello World\n" 
          "Copyright 1994 by WATCOM\n" ); 
  _dwSetAppTitle( "Hello World Application Title" ); 
  _dwSetConTitle( 0, "Hello World Console Title" ); 
  printf( "Hello World\n" ); 
  sec = fopen( "CON", "r+" ); 
  _dwSetConTitle( fileno( sec ), 
          "Hello World Second Console Title" ); 
  _dwDeleteOnClose( fileno( sec ) ); 
  fprintf( sec, "Hello to second console\n" ); 
  fprintf( sec, "Press Enter to close this console\n" ); 
  fflush( sec ); 
  fgetc( sec ); 
  fclose( sec ); 
  _dwShutDown(); 
  /* 
   do more computing that does not involve 
   console input/output 
  */ 
 } 

Classification: WATCOM 

Systems: Win, OS/2 2.x, NT


### _dwYield

Synopsis: 
#include <wdefwin.h> 
int _dwYield( void ); 

Description: The _dwYield function yields control back to the operating system, thereby giving other processes a chance to run. 
The _dwYield function is one of the support functions that can be called from an application using WATCOM's default windowing support. 

Returns: The _dwYield function returns 1 if it was successful and 0 if not. 

See Also: _dwDeleteOnClose, _dwSetAboutDlg, _dwSetAppTitle, _dwSetConTitle, _dwShutDown 

Example: 
#include <wdefwin.h> 
#include <stdio.h> 
void main() 
 { 
  int i; 
  for( i = 0; i < 1000; i++ ) { 
   /* give other processes a chance to run */ 
   _dwYield(); 
   /* do CPU-intensive calculation */ 
   /*  .  */ 
   /*  .  */ 
   /*  .  */ 
  } 
 } 

Classification: WATCOM 

Systems: Win, OS/2 2.x, NT


### ecvt

Synopsis: 
#include <stdlib.h> 
char *ecvt( double value, 
      int ndigits, 
      int *dec, 
      int *sign ); 

Description: The ecvt function converts the floating-point number value into a character string.  The parameter ndigits specifies the number of significant digits desired.  The converted number will be rounded to ndigits of precision. 
The character string will contain only digits and is terminated by a null character.  The integer pointed to by dec will be filled in with a value indicating the position of the decimal point relative to the start of the string of digits.  A zero or negative value indicates that the decimal point lies to the left of the first digit.  The integer pointed to by sign will contain 0 if the number is positive, and non-zero if the number is negative. 

Returns: The ecvt function returns a pointer to a static buffer containing the converted string of digits.  Note:  ecvt and  fcvt both use the same static buffer. 

See Also: fcvt, gcvt, printf 

Example: 
#include <stdio.h> 
#include <stdlib.h> 
void main() 
 { 
   char *str; 
   int  dec, sign; 
   str = ecvt( 123.456789, 6, &dec, &sign ); 
   printf( "str=%s, dec=%d, sign=%d\n", str,dec,sign ); 
 } 
produces the following: 
str=123457, dec=3, sign=0 

Classification: WATCOM 

Systems: All


### _ellipse, _ellipse_w, _ellipse_wxy

Synopsis: 
#include <graph.h> 
short _FAR _ellipse( short fill, short x1, short y1, 
                 short x2, short y2 ); 
short _FAR _ellipse_w( short fill, double x1, double y1, 
                  double x2, double y2 ); 
short _FAR _ellipse_wxy( short fill, 
             struct _wxycoord _FAR *p1, 
             struct _wxycoord _FAR *p2 ); 

Description: The _ellipse functions draw ellipses.  The _ellipse function uses the view coordinate system.  The _ellipse_w and _ellipse_wxy functions use the window coordinate system. 
The center of the ellipse is the center of the rectangle established by the points (x1,y1) and (x2,y2). 
The argument fill determines whether the ellipse is filled in or has only its outline drawn.  The argument can have one of two values: 

_GFILLINTERIOR fill the interior by writing pixels with the current plot action using the current color and the current fill mask 

_GBORDER leave the interior unchanged; draw the outline of the figure with the current plot action using the current color and line style 
When the coordinates (x1,y1) and (x2,y2) establish a line or a point (this happens when one or more of the x-coordinates or y-coordinates are equal), nothing is drawn. 

Returns: The _ellipse functions return a non-zero value when the ellipse was successfully drawn; otherwise, zero is returned. 

See Also: _arc, _rectangle, _setcolor, _setfillmask, _setlinestyle, _setplotaction 

Example: 
#include <conio.h> 
#include <graph.h> 
main() 
{ 
  _setvideomode( _VRES16COLOR ); 
  _ellipse( _GBORDER, 120, 90, 520, 390 ); 
  getch(); 
  _setvideomode( _DEFAULTMODE ); 
} 
produces the following: 
The graphical image cannot be reproduced here. See the printed 
version of the manual. 

Classification: PC Graphics 

Systems:  _ellipse - DOS, QNX 
_ellipse_w - DOS, QNX 
_ellipse_wxy - DOS, QNX


### _enable

Synopsis: 
#include <i86.h> 
void _enable( void ); 

Description: The _enable function causes interrupts to become enabled. 
The _enable function would be used in conjunction with the  _disable function to make sure that a sequence of instructions are executed without any intervening interrupts occurring. 

Returns: The _enable function returns no value. 

See Also: _disable 

Example: 
#include <stdio.h> 
#include <stdlib.h> 
#include <i86.h> 
struct list_entry { 
  struct list_entry *next; 
  int   data; 
}; 
struct list_entry *ListHead = NULL; 
struct list_entry *ListTail = NULL; 
void insert( struct list_entry *new_entry ) 
 { 
  /* insert new_entry at end of linked list */ 
  new_entry->next = NULL; 
  _disable();    /* disable interrupts */ 
  if( ListTail == NULL ) { 
   ListHead = new_entry; 
  } else { 
   ListTail->next = new_entry; 
  } 
  ListTail = new_entry; 
  _enable();     /* enable interrupts now */ 
 } 
void main() 
 { 
  struct list_entry *p; 
  int i; 
  for( i = 1; i <= 10; i++ ) { 
   p = (struct list_entry *) 
     malloc( sizeof( struct list_entry ) ); 
   if( p == NULL ) break; 
   p->data = i; 
   insert( p ); 
  } 
 } 

Classification: Intel 

Systems: All


### _endthread

Synopsis: 
#include <process.h> 
void __far _endthread(void); 

Description: The _endthread function uses the OS/2 function  DosExit to end the current thread of execution. 

Returns: The _endthread function does not return any value. 

See Also: _beginthread 

Example: 
#include <stdio.h> 
#include <stdlib.h> 
#include <process.h> 
#define  STACK_SIZE  4096 
#if defined(__386__) 
 #define FAR 
#else 
 #define FAR __far 
#endif 
void FAR child( void FAR *parm ) 
 { 
  char * FAR *argv = (char * FAR *) parm; 
  int  i; 
  for( i = 0; argv[i]; i++ ) { 
   printf( "argv[%d] = %s\n", i, argv[i] ); 
  } 
  _endthread(); 
 } 
void main() 
 { 
  char *stack; 
  char *args[3]; 
  int  tid; 
  args[0] = "child"; 
  args[1] = "parm"; 
  args[2] = NULL; 
  stack = (char *) malloc( STACK_SIZE ); 
  tid = _beginthread( child, stack, STACK_SIZE, args ); 
 } 

Classification: OS/2 

Systems: OS/2 1.x(MT), OS/2 1.x(DL), OS/2 2.x, NT


### eof

Synopsis: 
#include <io.h> 
int eof( int handle ); 

Description: The eof function determines, at the operating system level, if the end of the file has been reached for the file whose file handle is given by handle.  Because the current file position is set following an input operation, the  eof function may be called to detect the end of the file before an input operation beyond the end of the file is attempted. 

Returns: The eof function returns 1 if the current file position is at the end of the file, 0 if the current file position is not at the end.  A return value of -1 indicates an error, and in this case  errno is set to indicate the error. 

Errors: When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

EBADF The handle argument is not a valid file handle. 

See Also: read 

Example: 
#include <stdio.h> 
#include <fcntl.h> 
#include <io.h> 
void main() 
 { 
  int handle, len; 
  char buffer[100]; 
  handle = open( "file", O_RDONLY ); 
  if( handle != -1 ) { 
   while( ! eof( handle ) ) { 
    len = read( handle, buffer, sizeof(buffer) - 1 ); 
    buffer[ len ] = '\0'; 
    printf( "%s", buffer ); 
   } 
   close( handle ); 
  } 
 } 

Classification: WATCOM 

Systems: All


### exec Functions

Synopsis: 
#include <process.h> 
int execl(  path, arg0, arg1..., argn, NULL ); 
int execle(  path, arg0, arg1..., argn, NULL, envp ); 
int execlp(  file, arg0, arg1..., argn, NULL ); 
int execlpe( file, arg0, arg1..., argn, NULL, envp ); 
int execv(  path, argv ); 
int execve(  path, argv, envp ); 
int execvp(  file, argv ); 
int execvpe( file, argv, envp ); 
 const char *path;       /* file name incl. path */ 
 const char *file;       /* file name       */ 
 const char *arg0, ..., *argn; /* arguments       */ 
 char *const argv[];      /* array of arguments  */ 
 char *const envp[];      /* environment strings  */ 

Description: The exec functions load and execute a new child process, named by path or file.  If the child process is successfully loaded, it replaces the current process in memory.  No return is made to the original program. 
The program is located by using the following logic in sequence: 

 1.An attempt is made to locate the program in the current working directory if no directory specification precedes the program name; otherwise, an attempt is made in the specified directory. 

 2.If no file extension is given, an attempt is made to find the program name, in the directory indicated in the first point, with .COM concatenated to the end of the program name. 

 3.If no file extension is given, an attempt is made to find the program name, in the directory indicated in the first point, with .EXE concatenated to the end of the program name. 

 4.When no directory specification is given as part of the program name, the  execlp,  execlpe,  execvp, and  execvpe functions will repeat the preceding three steps for each of the directories specified by the  PATH environment variable.  The command 
    
   path c:\myapps;d:\lib\applns 
indicates that the two directories 
    
   c:\myapps 
   d:\lib\applns 
are to be searched.  The DOS PATH command (without any directory specification) will cause the current path definition to be displayed. 
An error is detected when the program cannot be found. 
Arguments are passed to the child process by supplying one or more pointers to character strings as arguments in the exec call.  These character strings are concatenated with spaces inserted to separate the arguments to form one argument string for the child process.  The length of this concatenated string must not exceed 128 bytes for DOS systems. 
The arguments may be passed as a list of arguments ( execl,  execle,  execlp, and  execlpe) or as a vector of pointers ( execv,  execve,  execvp, and  execvpe).  At least one argument, arg0 or argv[0], must be passed to the child process.  By convention, this first argument is a pointer to the name of the program. 
If the arguments are passed as a list, there must be a NULL pointer to mark the end of the argument list.  Similarly, if a pointer to an argument vector is passed, the argument vector must be terminated by a NULL pointer. 
The environment for the invoked program is inherited from the parent process when you use the  execl,  execlp,  execv, and  execvp functions.  The  execle,  execlpe,  execve, and  execvpe functions allow a different environment to be passed to the child process through the envp argument.  The argument envp is a pointer to an array of character pointers, each of which points to a string defining an environment variable.  The array is terminated with a NULL pointer.  Each pointer locates a character string of the form 
    
     variable=value 
that is used to define an environment variable.  If the value of envp is NULL, then the child process inherits the environment of the parent process. 
The environment is the collection of environment variables whose values have been defined with the DOS SET command or by the successful execution of the  putenv function.  A program may read these values with the  getenv function. 
The  execvpe and  execlpe functions are extensions to POSIX 1003.1. 

Returns: When the invoked program is successfully initiated, no return occurs.  When an error is detected while invoking the indicated program, exec returns -1 and  errno is set to indicate the error. 

Errors: When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

E2BIG The argument list exceeds 128 bytes, or the space required for the environment information exceeds 32K. 

EACCES The specified file has a locking or sharing violation. 

EMFILE Too many files open 

ENOENT Path or file not found 

ENOMEM Not enough memory is available to execute the child process. 

See Also: abort, atexit, exit, _exit, getcmd, getenv, main, putenv, spawn Functions, system 

Example: 
#include <stddef.h> 
#include <process.h> 
execl( "myprog", 
    "myprog", "ARG1", "ARG2", NULL ); 
The preceding invokes "myprog" as if 
  myprog ARG1 ARG2 
had been entered as a command to DOS.  The program will be found if one of 
  myprog. 
  myprog.com 
  myprog.exe 
is found in the current working directory. 
#include <stddef.h> 
#include <process.h> 
char *env_list[] = { "SOURCE=MYDATA", 
           "TARGET=OUTPUT", 
           "lines=65", 
           NULL 
          }; 
execle( "myprog", 
    "myprog", "ARG1", "ARG2", NULL, 
     env_list ); 
The preceding invokes "myprog" as if 
  myprog ARG1 ARG2 
had been entered as a command to DOS.  The program will be found if one of 
  myprog. 
  myprog.com 
  myprog.exe 
is found in the current working directory.  The DOS environment for the invoked program will consist of the three environment variables SOURCE, TARGET and lines. 
#include <stddef.h> 
#include <process.h> 
char *arg_list[] = { "myprog", "ARG1", "ARG2", NULL }; 
execv( "myprog", arg_list ); 
The preceding invokes "myprog" as if 
  myprog ARG1 ARG2 
had been entered as a command to DOS.  The program will be found if one of 
  myprog. 
  myprog.com 
  myprog.exe 
is found in the current working directory. 

Classification: POSIX 1003.1 with extensions 

Systems:  execl - DOS/16, QNX, OS/2 1.x(all), OS/2 2.x, NT 
execle - DOS/16, QNX, OS/2 1.x(all), OS/2 2.x, NT 
execlp - DOS/16, QNX, OS/2 1.x(all), OS/2 2.x, NT 
execlpe - DOS/16, QNX, OS/2 1.x(all), OS/2 2.x, NT 
execv - DOS/16, QNX, OS/2 1.x(all), OS/2 2.x, NT 
execve - DOS/16, QNX, OS/2 1.x(all), OS/2 2.x, NT 
execvp - DOS/16, QNX, OS/2 1.x(all), OS/2 2.x, NT 
execvpe - DOS/16, QNX, OS/2 1.x(all), OS/2 2.x, NT


### _exit

Synopsis: 
#include <stdlib.h> 
void _exit( int status ); 

Description: The _exit function causes normal program termination to occur. 

 1.The functions registered by the  atexit or  onexit functions are not called. 

 2.Any unopened files are not closed and any buffered output is not flushed to the associated files or devices. 

 3.Any files created by  tmpfile are not removed. 

 4.The return status is made available to the parent process.  Only the low order byte of status is available on DOS systems.  The status value is typically set to 0 to indicate successful termination and set to some other value to indicate an error. 

Returns: The _exit function does not return to its caller. 

See Also: abort, atexit, _bgetcmd, exec Functions, exit, getcmd, getenv, main, onexit, putenv, spawn Functions, system 

Example: 
#include <stdio.h> 
#include <stdlib.h> 
void main( int argc, char *argv[] ) 
 { 
  FILE *fp; 
  if( argc <= 1 ) { 
   fprintf( stderr, "Missing argument\n" ); 
   exit( EXIT_FAILURE ); 
  } 
  fp = fopen( argv[1], "r" ); 
  if( fp == NULL ) { 
   fprintf( stderr, "Unable to open '%s'\n", argv[1] ); 
   _exit( EXIT_FAILURE ); 
  } 
  fclose( fp ); 
  _exit( EXIT_SUCCESS ); 
 } 

Classification: POSIX 1003.1 

Systems: All


### exit

Synopsis: 
#include <stdlib.h> 
void exit( int status ); 

Description: The exit function causes normal program termination to occur. 
First, all functions registered by the  atexit function are called in the reverse order of their registration.  Next, all open files are flushed and closed, and all files created by the  tmpfile function are removed.  Finally, the return status is made available to the parent process.  Only the low order byte of status is available on DOS systems.  The status value is typically set to 0 to indicate successful termination and set to some other value to indicate an error. 

Returns: The exit function does not return to its caller. 

See Also: abort, atexit, _exit, onexit 

Example: 
#include <stdio.h> 
#include <stdlib.h> 
void main( int argc, char *argv[] ) 
 { 
  FILE *fp; 
  if( argc <= 1 ) { 
   fprintf( stderr, "Missing argument\n" ); 
   exit( EXIT_FAILURE ); 
  } 
  fp = fopen( argv[1], "r" ); 
  if( fp == NULL ) { 
   fprintf( stderr, "Unable to open '%s'\n", argv[1] ); 
   exit( EXIT_FAILURE ); 
  } 
  fclose( fp ); 
  exit( EXIT_SUCCESS ); 
 } 

Classification: ANSI 

Systems: All


### exp

Synopsis: 
#include <math.h> 
double exp( double x ); 

Description: The exp function computes the exponential function of x.  A range error occurs if the magnitude of x is too large. 

Returns: The exp function returns the exponential value.  When the argument is outside the permissible range, the  matherr function is called.  Unless the default  matherr function is replaced, it will set the global variable  errno to  ERANGE, and print a "RANGE error" diagnostic message using the  stderr stream. 

See Also: log, matherr 

Example: 
#include <stdio.h> 
#include <math.h> 
void main() 
 { 
  printf( "%f\n", exp(.5) ); 
 } 
produces the following: 
1.648721 

Classification: ANSI 

Systems: All


### _expand Functions

Synopsis: 
#include <malloc.h> 
void     *_expand( void *mem_blk, size_t size ); 
void __based(void) *_bexpand( __segment seg, 
               void __based(void) *mem_blk, 
               size_t size ); 
void __far  *_fexpand(void __far  *mem_blk,size_t size); 
void __near *_nexpand(void __near *mem_blk,size_t size); 

Description: The  _expand functions change the size of the previously allocated block pointed to by mem_blk by attempting to expand or contract the memory block without moving its location in the heap.  The argument size specifies the new desired size for the memory block.  The contents of the memory block are unchanged up to the shorter of the new and old sizes. 
Each function expands the memory from a particular heap, as listed below: 

_expand Depends on data model of the program 

_bexpand Based heap specified by seg value 

_fexpand Far heap (outside the default data segment) 

_nexpand Near heap (inside the default data segment) 
In a small data memory model, the  _expand function is equivalent to the  _nexpand function; in a large data memory model, the  _expand function is equivalent to the  _fexpand function. 

Returns: The  _expand functions return the value mem_blk if it was successful in changing the size of the block.  The return value is NULL (_NULLOFF for  _bexpand) if the memory block could not be expanded to the desired size.  It will be expanded as much as possible in this case. 
The appropriate  _msize function can be used to determine the new size of the expanded block. 

See Also: calloc Functions, free Functions, halloc, hfree, malloc Functions, _msize Functions, realloc Functions, sbrk 

Example: 
#include <stdio.h> 
#include <malloc.h> 
void main() 
 { 
  char *buf; 
  char __far *buf2; 
  buf = (char *) malloc( 80 ); 
  printf( "Size of buffer is %u\n", _msize(buf) ); 
  if( _expand( buf, 100 ) == NULL ) { 
    printf( "Unable to expand buffer\n" ); 
  } 
  printf( "New size of buffer is %u\n", _msize(buf) ); 
  buf2 = (char __far *) _fmalloc( 2000 ); 
  printf( "Size of far buffer is %u\n", _fmsize(buf2) ); 
  if( _fexpand( buf2, 8000 ) == NULL ) { 
    printf( "Unable to expand far buffer\n" ); 
  } 
  printf( "New size of far buffer is %u\n", 
       _fmsize(buf2) ); 
 } 
produces the following: 
Size of buffer is 80 
Unable to expand buffer 
New size of buffer is 80 
Size of far buffer is 2000 
New size of far buffer is 8000 

Classification: WATCOM 

Systems:  _expand - All 
_bexpand - DOS/16, Win/16, QNX/16, OS/2 1.x(all) 
_fexpand - DOS/16, Win/16, QNX/16, OS/2 1.x(all) 
_nexpand - DOS, Win, QNX, OS/2 1.x, OS/2 1.x(MT), OS/2 2.x, NT


### fabs

Synopsis: 
#include <math.h> 
double fabs( double x ); 

Description: The fabs function computes the absolute value of the argument x. 

Returns: The fabs function returns the absolute value of x. 

See Also: abs, labs 

Example: 
#include <stdio.h> 
#include <math.h> 
void main() 
 { 
  printf( "%f %f\n", fabs(.5), fabs(-.5) ); 
 } 
produces the following: 
0.500000 0.500000 

Classification: ANSI 

Systems: All


### fclose

Synopsis: 
#include <stdio.h> 
int fclose( FILE *fp ); 

Description: The fclose function closes the file fp.  If there was any unwritten buffered data for the file, it is written out before the file is closed.  Any unread buffered data is discarded.  If the associated buffer was automatically allocated, it is deallocated. 

Returns: The fclose function returns zero if the file was successfully closed, or non-zero if any errors were detected.  When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

See Also: fcloseall, fdopen, fopen, freopen, _fsopen 

Example: 
#include <stdio.h> 
void main() 
 { 
  FILE *fp; 
  fp = fopen( "stdio.h", "r" ); 
  if( fp != NULL ) { 
    fclose( fp ); 
  } 
 } 

Classification: ANSI 

Systems: All


### fcloseall

Synopsis: 
#include <stdio.h> 
int fcloseall( void ); 

Description: The fcloseall function closes all open stream files, except  stdin,  stdout,  stderr,  stdaux, and  stdprn.  This includes streams created (and not yet closed) by  fdopen,  fopen and  freopen. 

Returns: The fcloseall function returns the number of streams that were closed if no errors were encountered.  When an error occurs,  EOF is returned. 

See Also: fclose, fdopen, fopen, freopen, _fsopen 

Example: 
#include <stdio.h> 
void main() 
 { 
  printf( "The number of files closed is %d\n", 
      fcloseall() ); 
 } 

Classification: WATCOM 

Systems: All


### fcvt

Synopsis: 
#include <stdlib.h> 
char *fcvt( double value, 
      int ndigits, 
      int *dec, 
      int *sign ); 

Description: The fcvt function converts the floating-point number value into a character string.  The parameter ndigits specifies the number of digits desired after the decimal point.  The converted number will be rounded to this position. 
The character string will contain only digits and is terminated by a null character.  The integer pointed to by dec will be filled in with a value indicating the position of the decimal point relative to the start of the string of digits.  A zero or negative value indicates that the decimal point lies to the left of the first digit.  The integer pointed to by sign will contain 0 if the number is positive, and non-zero if the number is negative. 

Returns: The fcvt function returns a pointer to a static buffer containing the converted string of digits.  Note:  ecvt and  fcvt both use the same static buffer. 

See Also: ecvt, gcvt, printf 

Example: 
#include <stdio.h> 
#include <stdlib.h> 
void main() 
 { 
   char *str; 
   int  dec, sign; 
   str = fcvt( -123.456789, 5, &dec, &sign ); 
   printf( "str=%s, dec=%d, sign=%d\n", str,dec,sign ); 
 } 
produces the following: 
str=12345679, dec=3, sign=-1 

Classification: WATCOM 

Systems: All


### fdopen

Synopsis: 
#include <stdio.h> 
FILE *fdopen( int handle, const char *mode ); 

Description: The fdopen function associates a stream with the file handle handle which represents an opened file or device.  The handle was returned by one of  creat,  dup,  dup2,  open, or  sopen.  The open mode mode must match the mode with which the file or device was originally opened. 
The argument mode is described in the description of the  fopen function. 

Returns: The fdopen function returns a pointer to the object controlling the stream.  This pointer must be passed as a parameter to subsequent functions for performing operations on the file.  If the open operation fails, fdopen returns a NULL pointer.  When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

See Also: creat, dup, dup2, fopen, freopen, _fsopen, open, sopen 

Example: 
#include <stdio.h> 
#include <fcntl.h> 
#include <io.h> 
void main() 
 { 
  int handle; 
  FILE *fp; 
  handle = open( "file", O_RDONLY | O_TEXT ); 
  if( handle != -1 ) { 
   fp = fdopen( handle, "r" ); 
   if( fp != NULL ) { 
     fclose( fp ); 
   } 
   close( handle ); 
  } 
 } 

Classification: POSIX 1003.1 

Systems: All


### feof

Synopsis: 
#include <stdio.h> 
int feof( FILE *fp ); 

Description: The feof function tests the end-of-file indicator for the stream pointed to by fp.  Because this indicator is set when an input operation attempts to read past the end of the file the feof function will detect the end of the file only after an attempt is made to read beyond the end of the file.  Thus, if a file contains 10 lines, the feof will not detect end of file after the tenth line is read; it will detect end of file once the program attempts to read more data. 

Returns: The feof function returns non-zero if the end-of-file indicator is set for fp. 

See Also: clearerr, fopen, freopen, read, ferror, perror 

Example: 
#include <stdio.h> 
void main() 
 { 
  FILE *fp; 
  char buffer[100]; 
  fp = fopen( "file", "r" ); 
  fgets( buffer, sizeof( buffer ), fp ); 
  while( ! feof( fp ) ) { 
   process_record( buffer ); 
   fgets( buffer, sizeof( buffer ), fp ); 
  } 
  fclose( fp ); 
 } 
void process_record( char *buf ) 
 { 
  printf( "%s\n", buf ); 
 } 

Classification: ANSI 

Systems: All


### ferror

Synopsis: 
#include <stdio.h> 
int ferror( FILE *fp ); 

Description: The ferror function tests the error indicator for the stream pointed to by fp. 

Returns: The ferror function returns non-zero if the error indicator is set for fp. 

See Also: clearerr, feof, perror, strerror 

Example: 
#include <stdio.h> 
void main() 
 { 
  FILE *fp; 
  int c; 
  fp = fopen( "file", "r" ); 
  if( fp != NULL ) { 
   c = fgetc( fp ); 
   if( ferror( fp ) ) { 
    printf( "Error reading file\n" ); 
   } 
  } 
  fclose( fp ); 
 } 

Classification: ANSI 

Systems: All


### fflush

Synopsis: 
#include <stdio.h> 
int fflush( FILE *fp ); 

Description: If the file fp is open for output or update, the fflush function causes any unwritten data to be written to the file.  If the file fp is open for input or update, the fflush function undoes the effect of any preceding  ungetc operation on the stream.  If the value of fp is NULL, then all files that are open will be flushed. 

Returns: The fflush function returns non-zero if a write error occurs and zero otherwise.  When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

See Also: fgetc, fgets, flushall, fopen, getc, gets, setbuf, setvbuf, ungetc 

Example: 
#include <stdio.h> 
#include <conio.h> 
void main() 
 { 
  printf( "Press any key to continue..." ); 
  fflush( stdout ); 
  getch(); 
 } 

Classification: ANSI 

Systems: All


### fgetc

Synopsis: 
#include <stdio.h> 
int fgetc( FILE *fp ); 

Description: The fgetc function gets the next character from the file designated by fp.  The character is signed. 

Returns: The fgetc function returns the next character from the input stream pointed to by fp.  If the stream is at end-of-file, the end-of-file indicator is set and fgetc returns  EOF.  If a read error occurs, the error indicator is set and fgetc returns  EOF.  When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

See Also: fgetchar, fgets, fopen, getc, gets, ungetc 

Example: 
#include <stdio.h> 
void main() 
 { 
  FILE *fp; 
  int c; 
  fp = fopen( "file", "r" ); 
  if( fp != NULL ) { 
   while( (c = fgetc( fp )) != EOF ) 
    fputc( c, stdout ); 
   fclose( fp ); 
  } 
 } 

Classification: ANSI 

Systems: All


### fgetchar

Synopsis: 
#include <stdio.h> 
int fgetchar( void ); 

Description: The fgetchar function is equivalent to  fgetc with the argument  stdin. 

Returns: The fgetchar function returns the next character from the input stream pointed to by  stdin.  If the stream is at end-of-file, the end-of-file indicator is set and fgetchar returns  EOF.  If a read error occurs, the error indicator is set and fgetchar returns  EOF.  When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

See Also: fgetc, getc, getchar 

Example: 
#include <stdio.h> 
void main() 
 { 
  FILE *fp; 
  int c; 
  fp = freopen( "file", "r", stdin ); 
  if( fp != NULL ) { 
   while( (c = fgetchar()) != EOF ) 
    fputchar(c); 
   fclose( fp ); 
  } 
 } 

Classification: WATCOM 

Systems: All


### fgetpos

Synopsis: 
#include <stdio.h> 
int fgetpos( FILE *fp, fpos_t *pos ); 

Description: The fgetpos function stores the current position of the file fp in the object pointed to by pos.  The value stored is usable by the  fsetpos function for repositioning the file to its position at the time of the call to the  fgetpos function. 

Returns: The fgetpos function returns zero if successful, otherwise, the fgetpos function returns a non-zero value.  When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

See Also: fopen, fseek, fsetpos, ftell 

Example: 
#include <stdio.h> 
void main() 
 { 
  FILE *fp; 
  fpos_t position; 
  auto char buffer[80]; 
  fp = fopen( "file", "r" ); 
  if( fp != NULL ) { 
   fgetpos( fp, &position ); /* get position   */ 
   fgets( buffer, 80, fp );  /* read record    */ 
   fsetpos( fp, &position ); /* set position   */ 
   fgets( buffer, 80, fp );  /* read same record */ 
   fclose( fp ); 
  } 
 } 

Classification: ANSI 

Systems: All


### fgets

Synopsis: 
#include <stdio.h> 
char *fgets( char *buf, size_t n, FILE *fp ); 

Description: The fgets function gets a string of characters from the file designated by fp and stores them in the array pointed to by buf.  The fgets function stops reading characters when end-of-file is reached, or when a newline character is read, or when n-1 characters have been read, whichever comes first.  The new-line character is not discarded.  A null character is placed immediately after the last character read into the array. 
A common programming error is to assume the presence of a new-line character in every string that is read into the array.  A new-line character will not be present when more than n-1 characters occur before the new-line.  Also, a new-line character may not appear as the last character in a file, just before end-of-file. 
The  gets function is similar to fgets except that it operates with stdin, it has no size argument, and it replaces a newline character with the null character. 

Returns: The fgets function returns buf if successful.  NULL is returned if end-of-file is encountered, or a read error occurs.  When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

See Also: fopen, getc, gets, fgetc 

Example: 
#include <stdio.h> 
void main() 
 { 
  FILE *fp; 
  char buffer[80]; 
  fp = fopen( "file", "r" ); 
  if( fp != NULL ) { 
   while( fgets( buffer, 80, fp ) != NULL ) 
    fputs( buffer, stdout ); 
   fclose( fp ); 
  } 
 } 

Classification: ANSI 

Systems: All


### filelength

Synopsis: 
#include <io.h> 
long int filelength( int handle ); 

Description: The filelength function returns the number of bytes in the opened file indicated by the file handle handle. 

Returns: If an error occurs, (-1L) is returned.  When an error has occurred,  errno contains a value indicating the type of error that has been detected. 
Otherwise, the number of bytes written to the file is returned. 

See Also: fstat, lseek, tell 

Example: 
#include <sys/types.h> 
#include <fcntl.h> 
#include <stdio.h> 
#include <io.h> 
void main() 
 { 
  int handle; 
  /* open a file for input        */ 
  handle = open( "file", O_RDONLY | O_TEXT ); 
  if( handle != -1 ) { 
   printf( "Size of file is %ld bytes\n", 
       filelength( handle ) ); 
   close( handle ); 
  } 
 } 
produces the following: 
Size of file is 461 bytes 

Classification: WATCOM 

Systems: All


### fileno

Synopsis: 
#include <stdio.h> 
int fileno( FILE *stream ); 

Description: The fileno function returns the number of the file handle for the file designated by stream.  This number can be used in POSIX input/output calls anywhere the value returned by  open can be used.  The following symbolic values in <io.h> define the file handles that are associated with the C language stdin, stdout, stderr, stdaux, and stdprn files when the application is started. 

STDIN_FILENO Standard input file number, stdin (0) 

STDOUT_FILENO Standard output file number, stdout (1) 

STDERR_FILENO Standard error file number, stderr (2) 

STDAUX_FILENO Standard auxiliary file number, stdaux (3) 

STDPRN_FILENO Standard printer file number, stdprn (4) 

Returns: The fileno function returns the number of the file handle for the file designated by stream.  If an error occurs, a value of -1 is returned and  errno is set to indicate the error. 

See Also: open 

Example: 
#include <stdio.h> 
void main() 
 { 
  FILE *stream; 
  stream = fopen( "file", "r" ); 
  printf( "File number is %d\n", fileno( stream ) ); 
  fclose( stream ); 
 } 
produces the following: 
File number is 7 

Classification: POSIX 1003.1 

Systems: All


### _floodfill, _floodfill_w

Synopsis: 
#include <graph.h> 
short _FAR _floodfill( short x, short y, 
            short stop_color ); 
short _FAR _floodfill_w( double x, double y, 
             short stop_color ); 

Description: The _floodfill functions fill an area of the screen.  The _floodfill function uses the view coordinate system.  The _floodfill_w function uses the window coordinate system. 
The filling starts at the point (x,y) and continues in all directions:  when a pixel is filled, the neighbouring pixels (horizontally and vertically) are then considered for filling.  Filling is done using the current color and fill mask.  No filling will occur if the point (x,y) lies outside the clipping region. 
If the argument stop_color is a valid pixel value, filling will occur in each direction until a pixel is encountered with a pixel value of stop_color.  The filled area will be the area around (x,y), bordered by stop_color.  No filling will occur if the point (x,y) has the pixel value stop_color. 
If stop_color has the value (-1), filling occurs until a pixel is encountered with a pixel value different from the pixel value of the starting point (x,y). No filling will occur if the pixel value of the point (x,y) is the current color. 

Returns: The _floodfill functions return zero when no filling takes place; a non-zero value is returned to indicate that filling has occurred. 

See Also: _setcliprgn, _setcolor, _setfillmask, _setplotaction 

Example: 
#include <conio.h> 
#include <graph.h> 
main() 
{ 
  _setvideomode( _VRES16COLOR ); 
  _setcolor( 1 ); 
  _ellipse( _GBORDER, 120, 90, 520, 390 ); 
  _setcolor( 2 ); 
  _floodfill( 320, 240, 1 ); 
  getch(); 
  _setvideomode( _DEFAULTMODE ); 
} 

Classification: PC Graphics 

Systems:  _floodfill - DOS, QNX 
_floodfill_w - DOS, QNX


### floor

Synopsis: 
#include <math.h> 
double floor( double x ); 

Description: The floor function computes the largest integer not greater than x. 

Returns: The floor function computes the largest integer not greater than x, expressed as a double. 

See Also: ceil, fmod 

Example: 
#include <stdio.h> 
#include <math.h> 
void main() 
 { 
  printf( "%f\n", floor( -3.14 ) ); 
  printf( "%f\n", floor( -3. ) ); 
  printf( "%f\n", floor( 0. ) ); 
  printf( "%f\n", floor( 3.14 ) ); 
  printf( "%f\n", floor( 3. ) ); 
 } 
produces the following: 
-4.000000 
-3.000000 
0.000000 
3.000000 
3.000000 

Classification: ANSI 

Systems: All


### flushall

Synopsis: 
#include <stdio.h> 
int flushall( void ); 

Description: The flushall function clears all buffers associated with input streams and writes any buffers associated with output streams.  A subsequent read operation on an input file causes new data to be read from the associated file or device. 
The function is equivalent to calling the  fflush for all open stream files. 

Returns: The flushall function returns the number of open streams.  When an output error occurs while writing to a file, the  errno global variable will be set. 

See Also: fopen, fflush 

Example: 
#include <stdio.h> 
void main() 
 { 
  printf( "The number of open files is %d\n", 
      flushall() ); 
 } 
produces the following: 
The number of open files is 4 

Classification: WATCOM 

Systems: All


### fmod

Synopsis: 
#include <math.h> 
double fmod( double x, double y ); 

Description: The fmod function computes the floating-point remainder of x/y, even if the quotient x/y is not representable. 

Returns: The fmod function returns the value x - (i * y), for some integer i such that, if y is non-zero, the result has the same sign as x and magnitude less than the magnitude of y.  If the value of y is zero, then the value returned is zero. 

See Also: ceil, fabs, floor 

Example: 
#include <stdio.h> 
#include <math.h> 
void main() 
 { 
  printf( "%f\n", fmod(  4.5,  2.0 ) ); 
  printf( "%f\n", fmod( -4.5,  2.0 ) ); 
  printf( "%f\n", fmod(  4.5, -2.0 ) ); 
  printf( "%f\n", fmod( -4.5, -2.0 ) ); 
 } 
produces the following: 
0.500000 
-0.500000 
0.500000 
-0.500000 

Classification: ANSI 

Systems: All


### fopen

Synopsis: 
#include <stdio.h> 
FILE *fopen( const char *filename, const char *mode ); 

Description: The fopen function opens the file whose name is the string pointed to by filename, and associates a stream with it.  The argument mode points to a string beginning with one of the following sequences: 

"r" open file for reading; use default file translation 

"w" create file for writing, or truncate to zero length; use default file translation 

"a" append:  open text file or create for writing at end-of-file; use default file translation 

"rb" open binary file for reading 

"rt" open text file for reading 

"wb" create binary file for writing, or truncate to zero length 

"wt" create text file for writing, or truncate to zero length 

"ab" append; open binary file or create for writing at end-of-file 

"at" append; open text file or create for writing at end-of-file 

"r+" open file for update (reading and/or writing); use default file translation 

"w+" create file for update, or truncate to zero length; use default file translation 

"a+" append; open file or create for update, writing at end-of-file; use default file translation 

"r+b", "rb+" open binary file for update (reading and/or writing) 

"r+t", "rt+" open text file for update (reading and/or writing) 

"w+b", "wb+" create binary file for update, or truncate to zero length 

"w+t", "wt+" create text file for update, or truncate to zero length 

"a+b", "ab+" append; open binary file or create for update, writing at end-of-file 

"a+t", "at+" append; open text file or create for update, writing at end-of-file 
When default file translation is specified, the value of the global variable  _fmode establishes whether the file is to treated as a binary or a text file.  Unless this value is changed by the program, the default will be text mode. 
Opening a file with read mode ('r' as the first character in the mode argument) fails if the file does not exist or it cannot be read.  Opening a file with append mode ('a' as the first character in the mode argument) causes all subsequent writes to the file to be forced to the current end-of-file, regardless of previous calls to the  fseek function.  When a file is opened with update mode ('+' as the second or third character of the mode argument), both input and output may be performed on the associated stream. 
When a stream is opened in update mode, both reading and writing may be performed.  However, writing may not be followed by reading without an intervening call to the  fflush function or to a file positioning function ( fseek,  fsetpos,  rewind).  Similarly, reading may not be followed by writing without an intervening call to a file positioning function, unless the read resulted in end-of-file. 

Returns: The fopen function returns a pointer to the object controlling the stream.  This pointer must be passed as a parameter to subsequent functions for performing operations on the file.  If the open operation fails, fopen returns NULL.  When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

See Also: fclose, fcloseall, fdopen, freopen, _fsopen 

Example: 
#include <stdio.h> 
void main() 
 { 
  FILE *fp; 
  fp = fopen( "report.dat", "r" ); 
  if( fp != NULL ) { 
   /* rest of code goes here */ 
   fclose( fp ); 
  } 
 } 

Classification: ANSI, ('t' is a WATCOM extension) 

Systems: All


### FP_OFF

Synopsis: 
#include <i86.h> 
unsigned FP_OFF( void __far *far_ptr ); 

Description: The FP_OFF macro can be used to obtain the offset portion of the far pointer value given in far_ptr. 

Returns: The macro returns an unsigned integer value which is the offset portion of the pointer value. 

See Also: FP_SEG, MK_FP, segread 

Example: 
#include <stdio.h> 
#include <i86.h> 
char ColourTable[256][3]; 
void main() 
 { 
  union REGPACK r; 
  int i; 
  /* read block of colour registers */ 
  r.h.ah = 0x10; 
  r.h.al = 0x17; 
#if defined(__386__) 
  r.x.ebx = 0; 
  r.x.ecx = 256; 
  r.x.edx = FP_OFF( ColourTable ); 
  r.w.ds = r.w.fs = r.w.gs = FP_SEG( &r ); 
#else 
  r.w.bx = 0; 
  r.w.cx = 256; 
  r.w.dx = FP_OFF( ColourTable ); 
#endif 
  r.w.es = FP_SEG( ColourTable ); 
  intr( 0x10, &r ); 
  for( i = 0; i < 256; i++ ) { 
   printf( "Colour index = %d " 
       "{ Red=%d, Green=%d, Blue=%d }\n", 
       i, 
       ColourTable[i][0], 
       ColourTable[i][1], 
       ColourTable[i][2] ); 
  } 
 } 

Classification: Intel 

Systems: MACRO


### FP_SEG

Synopsis: 
#include <i86.h> 
unsigned FP_SEG( void __far *far_ptr ); 

Description: The FP_SEG macro can be used to obtain the segment portion of the far pointer value given in far_ptr. 

Returns: The macro returns an unsigned integer value which is the segment portion of the pointer value. 

See Also: FP_OFF, MK_FP, segread 

Example: 
#include <stdio.h> 
#include <i86.h> 
char ColourTable[256][3]; 
void main() 
 { 
  union REGPACK r; 
  int i; 
  /* read block of colour registers */ 
  r.h.ah = 0x10; 
  r.h.al = 0x17; 
#if defined(__386__) 
  r.x.ebx = 0; 
  r.x.ecx = 256; 
  r.x.edx = FP_OFF( ColourTable ); 
  r.w.ds = r.w.fs = r.w.gs = FP_SEG( &r ); 
#else 
  r.w.bx = 0; 
  r.w.cx = 256; 
  r.w.dx = FP_OFF( ColourTable ); 
#endif 
  r.w.es = FP_SEG( ColourTable ); 
  intr( 0x10, &r ); 
  for( i = 0; i < 256; i++ ) { 
   printf( "Colour index = %d " 
       "{ Red=%d, Green=%d, Blue=%d }\n", 
       i, 
       ColourTable[i][0], 
       ColourTable[i][1], 
       ColourTable[i][2] ); 
  } 
 } 

Classification: Intel 

Systems: MACRO


### _fpreset

Synopsis: 
#include <float.h> 
void _fpreset( void ); 

Description: After a floating-point exception, it may be necessary to call the _fpreset function before any further floating-point operations are attempted. 

Returns: No value is returned. 

See Also: _clear87, _status87 

Example: 
#include <stdio.h> 
#include <float.h> 
char *status[2] = { "No", "  " }; 
void main() 
 { 
  unsigned int fp_status; 
  fp_status = _status87(); 
  printf( "80x87 status\n" ); 
  printf( "%s invalid operation\n", 
      status[ (fp_status & SW_INVALID) == 0 ] ); 
  printf( "%s denormalized operand\n", 
      status[ (fp_status & SW_DENORMAL) == 0 ] ); 
  printf( "%s divide by zero\n", 
      status[ (fp_status & SW_ZERODIVIDE) == 0 ] ); 
  printf( "%s overflow\n", 
      status[ (fp_status & SW_OVERFLOW) == 0 ] ); 
  printf( "%s underflow\n", 
      status[ (fp_status & SW_UNDERFLOW) == 0 ] ); 
  printf( "%s inexact result\n", 
      status[ (fp_status & SW_INEXACT) == 0 ] ); 
  _fpreset(); 
 } 

Classification: Intel 

Systems: All


### fprintf

Synopsis: 
#include <stdio.h> 
int fprintf( FILE *fp, const char *format, ... ); 

Description: The fprintf function writes output to the file pointed to by fp under control of the argument format.  The format string is described under the description of the  printf function. 

Returns: The fprintf function returns the number of characters written, or a negative value if an output error occurred.  When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

See Also: _bprintf, cprintf, printf, sprintf, _vbprintf, vcprintf, vfprintf, vprintf, vsprintf 

Example: 
#include <stdio.h> 
char *weekday = { "Saturday" }; 
char *month = { "April" }; 
void main() 
 { 
  fprintf( stdout, "%s, %s %d, %d\n", 
     weekday, month, 18, 1987 ); 
 } 
produces the following: 
Saturday, April 18, 1987 

Classification: ANSI 

Systems: All


### fputc

Synopsis: 
#include <stdio.h> 
int fputc( int c, FILE *fp ); 

Description: The fputc function writes the character specified by the argument c to the output stream designated by fp. 

Returns: The fputc function returns the character written. If a write error occurs, the error indicator is set and fputc returns  EOF.  When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

See Also: fopen, fputchar, fputs, putc, putchar, puts 

Example: 
#include <stdio.h> 
void main() 
 { 
  FILE *fp; 
  int c; 
  fp = fopen( "file", "r" ); 
  if( fp != NULL ) { 
   while( (c = fgetc( fp )) != EOF ) 
    fputc( c, stdout ); 
   fclose( fp ); 
  } 
 } 

Classification: ANSI 

Systems: All


### fputchar

Synopsis: 
#include <stdio.h> 
int fputchar( int c ); 

Description: The fputchar function writes the character specified by the argument c to the output stream  stdout.  This function is identical to the  putchar function. 
The function is equivalent to: 
    
     fputc( c, stdout ); 

Returns: The fputchar function returns the character written.  If a write error occurs, the error indicator is set and fputchar returns  EOF.  When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

See Also: fputc, fputs, putc, putchar 

Example: 
#include <stdio.h> 
void main() 
 { 
  FILE *fp; 
  int c; 
  fp = fopen( "file", "r" ); 
  if( fp != NULL ) { 
   c = fgetc( fp ); 
   while( c != EOF ) { 
    fputchar( c ); 
    c = fgetc( fp ); 
   } 
   fclose( fp ); 
  } 
 } 

Classification: WATCOM 

Systems: All


### fputs

Synopsis: 
#include <stdio.h> 
int fputs( const char *buf, FILE *fp ); 

Description: The fputs function writes the character string pointed to by buf to the output stream designated by fp.  The terminating null character is not written. 

Returns: The fputs function returns EOF if an error occurs otherwise it returns a non-negative value.  When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

See Also: fopen, fputc, putc, puts 

Example: 
#include <stdio.h> 
void main() 
 { 
  FILE *fp; 
  char buffer[80]; 
  fp = fopen( "file", "r" ); 
  if( fp != NULL ) { 
   while( fgets( buffer, 80, fp ) != NULL ) 
    fputs( buffer, stdout ); 
   fclose( fp ); 
  } 
 } 

Classification: ANSI 

Systems: All


### fread

Synopsis: 
#include <stdio.h> 
size_t fread( void *buf, 
       size_t elsize, 
       size_t nelem, 
       FILE *fp ); 

Description: The fread function reads nelem elements of elsize bytes each from the file specified by fp into the buffer specified by buf. 

Returns: The fread function returns the number of complete elements successfully read.  This value may be less than the requested number of elements. 
The  feof and  ferror functions can be used to determine whether the end of the file was encountered or if an input/output error has occurred.  When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

See Also: fopen, feof, ferror 

Example: 
The following example reads a simple student record containing binary data.  The student record is described by the struct student_data declaration. 
#include <stdio.h> 
struct student_data { 
  int  student_id; 
  unsigned char marks[10]; 
}; 
size_t read_data( FILE *fp, struct student_data *p ) 
 { 
  return( fread( p, sizeof(*p), 1, fp ) ); 
 } 
void main() 
 { 
  FILE *fp; 
  struct student_data std; 
  int i; 
  fp = fopen( "file", "r" ); 
  if( fp != NULL ) { 
   while( read_data( fp, &std ) != 0 ) { 
    printf( "id=%d ", std.student_id ); 
    for( i = 0; i < 10; i++ ) 
     printf( "%3d ", std.marks[ i ] ); 
    printf( "\n" ); 
   } 
   fclose( fp ); 
  } 
 } 

Classification: ANSI 

Systems: All


### free Functions

Synopsis: 
#include <stdlib.h>  For ANSI compatibility (free only) 
#include <malloc.h>  Required for other function prototypes 
void free( void *ptr ); 
void _bfree( __segment seg, void __based(void) *ptr ); 
void _ffree( void __far  *ptr ); 
void _nfree( void __near *ptr ); 

Description: When the value of the argument ptr is NULL, the  free function does nothing; otherwise, the  free function deallocates the memory block located by the argument ptr which points to a memory block previously allocated through a call to the appropriate version of  calloc,  malloc or  realloc.  After the call, the freed block is available for allocation. 
Each function deallocates memory from a particular heap, as listed below: 

free Depends on data model of the program 

_bfree Based heap specified by seg value 

_ffree Far heap (outside the default data segment) 

_nfree Near heap (inside the default data segment) 
In a large data memory model, the  free function is equivalent to the  _ffree function; in a small data memory model, the  free function is equivalent to the  _nfree function. 

Returns: The  free functions return no value. 

See Also: calloc Functions, _expand Functions, halloc, hfree, malloc Functions, _msize Functions, realloc Functions, sbrk 

Example: 
#include <stdio.h> 
#include <stdlib.h> 
void main() 
 { 
  char *buffer; 
  buffer = (char *)malloc( 80 ); 
  if( buffer == NULL ) { 
   printf( "Unable to allocate memory\n" ); 
  } else { 
   /* rest of code goes here */ 
   free( buffer );  /* deallocate buffer */ 
  } 
 } 

Classification: free is ANSI; _bfree, _ffree, and _nfree are not ANSI 

Systems:  free - All 
_bfree - DOS/16, Win/16, QNX/16, OS/2 1.x(all) 
_ffree - DOS/16, Win/16, QNX/16, OS/2 1.x(all) 
_nfree - DOS, Win, QNX, OS/2 1.x, OS/2 1.x(MT), OS/2 2.x, NT


### _freect

Synopsis: 
#include <malloc.h> 
unsigned int _freect( size_t size ); 

Description: The _freect function returns the number of times that  _nmalloc (or  malloc in small data models) can be called to allocate a item of size bytes.  In the tiny, small and medium memory models, the default data segment is only extended as needed to satisfy requests for memory allocation.  Therefore, you will need to call  _nheapgrow in these memory models before calling _freect in order to get a meaningful result. 

Returns: The _freect function returns the number of calls as an unsigned integer. 

See Also: calloc, _heapgrow Functions, malloc Functions, _memavl, _memmax 

Example: 
#include <stdio.h> 
#include <malloc.h> 
void main() 
 { 
  int  i; 
  printf( "Can allocate %u longs before _nheapgrow\n", 
      _freect( sizeof(long) ) ); 
  _nheapgrow(); 
  printf( "Can allocate %u longs after _nheapgrow\n", 
      _freect( sizeof(long) ) ); 
  for( i = 1; i < 1000; i++ ) { 
   _nmalloc( sizeof(long) ); 
  } 
  printf( "After allocating 1000 longs:\n" ); 
  printf( "Can still allocate %u longs\n", 
      _freect( sizeof(long) ) ); 
 } 
produces the following: 
Can allocate 0 longs before _nheapgrow 
Can allocate 10447 longs after _nheapgrow 
After allocating 1000 longs: 
Can still allocate 9447 longs 

Classification: WATCOM 

Systems: All


### freopen

Synopsis: 
#include <stdio.h> 
FILE *freopen( const char *filename, 
        const char *mode, 
        FILE *fp ); 

Description: The stream located by the  fp pointer is closed.  The freopen function opens the file whose name is the string pointed to by filename, and associates a stream with it.  The stream information is placed in the structure located by the fp pointer. 
The argument mode is described in the description of the  fopen function. 

Returns: The  freopen function returns a pointer to the object controlling the stream.  This pointer must be passed as a parameter to subsequent functions for performing operations on the file.  If the open operation fails,  freopen returns NULL.  When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

See Also: fclose, fcloseall, fdopen, fopen, _fsopen 

Example: 
#include <stdio.h> 
void main() 
 { 
  FILE *fp; 
  int c; 
  fp = freopen( "file", "r", stdin ); 
  if( fp != NULL ) { 
   while( (c = fgetchar()) != EOF ) 
    fputchar(c); 
   fclose( fp ); 
  } 
 } 

Classification: ANSI 

Systems: All


### frexp

Synopsis: 
#include <math.h> 
double frexp( double value, int *exp ); 

Description: The frexp function breaks a floating-point number into a normalized fraction and an integral power of 2.  It stores the integral power of 2 in the int object pointed to by exp. 

Returns: The frexp function returns the value of x, such that x is a double with magnitude in the interval [0.5,1) or zero, and value equals x times 2 raised to the power *exp.  If value is zero, then both parts of the result are zero. 

See Also: ldexp, modf 

Example: 
#include <stdio.h> 
#include <math.h> 
void main() 
 { 
  int   expon; 
  double value; 
  value = frexp(  4.25, &expon ); 
  printf( "%f %d\n", value, expon ); 
  value = frexp( -4.25, &expon ); 
  printf( "%f %d\n", value, expon ); 
 } 
produces the following: 
0.531250 3 
-0.531250 3 

Classification: ANSI 

Systems: All


### fscanf

Synopsis: 
#include <stdio.h> 
int fscanf( FILE *fp, const char *format, ... ); 

Description: The fscanf function scans input from the file designated by fp under control of the argument format.  Following the format string is a list of addresses to receive values.  The format string is described under the description of the  scanf function. 

Returns: The fscanf function returns  EOF when the scanning is terminated by reaching the end of the input stream.  Otherwise, the number of input arguments for which values were successfully scanned and stored is returned.  When a file input error occurs, the  errno global variable may be set. 

See Also: cscanf, scanf, sscanf, vcscanf, vfscanf, vscanf, vsscanf 

Example: 
To scan a date in the form "Saturday April 18 1987": 
#include <stdio.h> 
void main() 
 { 
  int day, year; 
  char weekday[10], month[10]; 
  FILE *in_data; 
  in_data = fopen( "file", "r" ); 
  if( in_data != NULL ) { 
   fscanf( in_data, "%s %s %d %d", 
       weekday, month, &day, &year ); 
   printf( "Weekday=%s Month=%s Day=%d Year=%d\n", 
       weekday, month, day, year ); 
   fclose( in_data ); 
  } 
 } 

Classification: ANSI 

Systems: All


### fseek

Synopsis: 
#include <stdio.h> 
int fseek( FILE *fp, long int offset, int where ); 

Description: The fseek function changes the read/write position of the file specified by fp.  This position defines the character that will be read or written on the next I/O operation on the file.  The argument fp is a file pointer returned by  fopen or  freopen.  The argument offset is the position to seek to relative to one of three positions specified by the argument where.  Allowable values for where are: 

SEEK_SET The new file position is computed relative to the start of the file.  The value of offset must not be negative. 

SEEK_CUR The new file position is computed relative to the current file position.  The value of offset may be positive, negative or zero. 

SEEK_END The new file position is computed relative to the end of the file. 
The fseek function clears the end-of-file indicator and undoes any effects of the  ungetc function on the same file. 
The  ftell function can be used to obtain the current position in the file before changing it.  The position can be restored by using the value returned by  ftell in a subsequent call to  fseek with the where parameter set to SEEK_SET. 

Returns: The fseek function returns zero if successful, non-zero otherwise.  When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

See Also: fgetpos, fopen, fsetpos, ftell 

Example: 
The size of a file can be determined by the following example which saves and restores the current position of the file. 
#include <stdio.h> 
long int filesize( FILE *fp ) 
 { 
  long int save_pos, size_of_file; 
  save_pos = ftell( fp ); 
  fseek( fp, 0L, SEEK_END ); 
  size_of_file = ftell( fp ); 
  fseek( fp, save_pos, SEEK_SET ); 
  return( size_of_file ); 
 } 
void main() 
 { 
  FILE *fp; 
  fp = fopen( "file", "r" ); 
  if( fp != NULL ) { 
   printf( "File size=%ld\n", filesize( fp ) ); 
   fclose( fp ); 
  } 
 } 

Classification: ANSI 

Systems: All


### fsetpos

Synopsis: 
#include <stdio.h> 
int fsetpos( FILE *fp, fpos_t *pos ); 

Description: The fsetpos function positions the file fp according to the value of the object pointed to by pos, which shall be a value returned by an earlier call to the  fgetpos function on the same file. 

Returns: The fsetpos function returns zero if successful, otherwise, the fsetpos function returns a non-zero value.  When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

See Also: fgetpos, fopen, fseek, ftell 

Example: 
#include <stdio.h> 
void main() 
 { 
  FILE *fp; 
  fpos_t position; 
  auto char buffer[80]; 
  fp = fopen( "file", "r" ); 
  if( fp != NULL ) { 
   fgetpos( fp, &position ); /* get position   */ 
   fgets( buffer, 80, fp );  /* read record    */ 
   fsetpos( fp, &position ); /* set position   */ 
   fgets( buffer, 80, fp );  /* read same record */ 
   fclose( fp ); 
  } 
 } 

Classification: ANSI 

Systems: All


### _fsopen

Synopsis: 
#include <stdio.h> 
FILE *_fsopen( const char *filename, const char *mode, int share ); 

Description: The _fsopen function opens the file whose name is the string pointed to by filename, and associates a stream with it.  The arguments mode and share control shared reading or writing.  The argument mode points to a string beginning with one of the following sequences: 

"r" open file for reading; use default file translation 

"w" create file for writing, or truncate to zero length; use default file translation 

"a" append:  open text file or create for writing at end-of-file; use default file translation 

"rb" open binary file for reading 

"rt" open text file for reading 

"wb" create binary file for writing, or truncate to zero length 

"wt" create text file for writing, or truncate to zero length 

"ab" append; open binary file or create for writing at end-of-file 

"at" append; open text file or create for writing at end-of-file 

"r+" open file for update (reading and/or writing); use default file translation 

"w+" create file for update, or truncate to zero length; use default file translation 

"a+" append; open file or create for update, writing at end-of-file; use default file translation 

"r+b", "rb+" open binary file for update (reading and/or writing) 

"r+t", "rt+" open text file for update (reading and/or writing) 

"w+b", "wb+" create binary file for update, or truncate to zero length 

"w+t", "wt+" create text file for update, or truncate to zero length 

"a+b", "ab+" append; open binary file or create for update, writing at end-of-file 

"a+t", "at+" append; open text file or create for update, writing at end-of-file 
When default file translation is specified, the value of the global variable  _fmode establishes whether the file is to treated as a binary or a text file.  Unless this value is changed by the program, the default will be text mode. 
Opening a file with read mode ('r' as the first character in the mode argument) fails if the file does not exist or it cannot be read.  Opening a file with append mode ('a' as the first character in the mode argument) causes all subsequent writes to the file to be forced to the current end-of-file, regardless of previous calls to the  fseek function.  When a file is opened with update mode ('+' as the second or third character of the mode argument), both input and output may be performed on the associated stream. 
When a stream is opened in update mode, both reading and writing may be performed.  However, writing may not be followed by reading without an intervening call to the  fflush function or to a file positioning function ( fseek,  fsetpos,  rewind).  Similarly, reading may not be followed by writing without an intervening call to a file positioning function, unless the read resulted in end-of-file. 
The shared access for the file, share, is established by a combination of bits defined in the <share.h> header file.  The following values may be set: 

SH_COMPAT Set compatibility mode. 

SH_DENYRW Prevent read or write access to the file. 

SH_DENYWR Prevent write access of the file. 

SH_DENYRD Prevent read access to the file. 

SH_DENYNO Permit both read and write access to the file. 
You should consult the technical documentation for the DOS system that you are using for more detailed information about these sharing modes. 

Returns: The _fsopen function returns a pointer to the object controlling the stream.  This pointer must be passed as a parameter to subsequent functions for performing operations on the file.  If the open operation fails, _fsopen returns NULL.  When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

See Also: fclose, fcloseall, fdopen, fopen, freopen 

Example: 
#include <stdio.h> 
void main() 
 { 
  FILE *fp; 
  /* 
   open a file and prevent others from writing to it 
  */ 
  fp = _fsopen( "report.dat", "w", SH_DENYWR ); 
  if( fp != NULL ) { 
   /* rest of code goes here */ 
   fclose( fp ); 
  } 
 } 

Classification: WATCOM 

Systems: All


### fstat

Synopsis: 
#include <sys\types.h> 
#include <sys\stat.h> 
int fstat( int handle, struct stat *buf ); 

Description: The fstat function obtains information about an open file whose file handle is handle.  This information is placed in the structure located at the address indicated by buf. 
The file <sys\stat.h> contains definitions for the structure  stat. 
struct stat { 
  dev_t  st_dev;   /* disk drive file resides on */ 
  ino_t  st_ino;   /* this inode's number     */ 
  unsigned short st_mode; /* file mode       */ 
  short  st_nlink;  /* # of hard links       */ 
  short  st_uid;   /* user-id, always 'root'   */ 
  short  st_gid;   /* group-id, always 'root'   */ 
  dev_t  st_rdev;  /* drive #, same as st_dev   */ 
  off_t  st_size;  /* total file size       */ 
  time_t  st_atime;  /* time of last access     */ 
  time_t  st_mtime;  /* time of last modification  */ 
  time_t  st_ctime;  /* time of last status change */ 
}; 
At least the following macros are defined in the <sys\stat.h> header file. 

S_ISFIFO(m) Test for FIFO. 

S_ISCHR(m) Test for character special file. 

S_ISDIR(m) Test for directory file. 

S_ISBLK(m) Test for block special file. 

S_ISREG(m) Test for regular file. 
The value m supplied to the macros is the value of the  st_mode field of a  stat structure.  The macro evaluates to a non-zero value if the test is true and zero if the test is false. 
The following bits are encoded within the  st_mode field of a  stat structure. 

S_IRWXU Read, write, search (if a directory), or execute (otherwise) 

S_IRUSR Read permission bit 

S_IWUSR Write permission bit 

S_IXUSR Search/execute permission bit 

S_IREAD ==  S_IRUSR (for Microsoft compatibility) 

S_IWRITE ==  S_IWUSR (for Microsoft compatibility) 

S_IEXEC ==  S_IXUSR (for Microsoft compatibility) 
 S_IRWXU is the bitwise inclusive OR of  S_IRUSR,  S_IWUSR, and  S_IXUSR. 

S_IRWXG Read, write, search (if a directory), or execute (otherwise) 

S_IRGRP Read permission bit 

S_IWGRP Write permission bit 

S_IXGRP Search/execute permission bit 
 S_IRWXG is the bitwise inclusive OR of  S_IRGRP,  S_IWGRP, and  S_IXGRP. 

S_IRWXO Read, write, search (if a directory), or execute (otherwise) 

S_IROTH Read permission bit 

S_IWOTH Write permission bit 

S_IXOTH Search/execute permission bit 
 S_IRWXO is the bitwise inclusive OR of  S_IROTH,  S_IWOTH, and  S_IXOTH. 

S_ISUID (Not supported by DOS, OS/2 or Windows NT) Set user ID on execution.  The process's effective user ID shall be set to that of the owner of the file when the file is run as a program.  On a regular file, this bit should be cleared on any write. 

S_ISGID (Not supported by DOS, OS/2 or Windows NT) Set group ID on execution.  Set effective group ID on the process to the file's group when the file is run as a program.  On a regular file, this bit should be cleared on any write. 

Returns: The fstat function returns zero when the information is successfully obtained.  Otherwise, -1 is returned. 

Errors: When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

EBADF The handle argument is not a valid file handle. 

See Also: creat, dup, dup2, open, sopen, stat 

Example: 
#include <stdio.h> 
#include <sys\types.h> 
#include <sys\stat.h> 
#include <fcntl.h> 
#include <io.h> 
void main() 
 { 
  int handle, rc; 
  struct stat buf; 
  handle = open( "file", O_RDONLY ); 
  if( handle != -1 ) { 
   rc = fstat( handle, &buf ); 
   if( rc != -1 ) 
    printf( "File size = %d\n", buf.st_size ); 
   close( handle ); 
  } 
 } 

Classification: POSIX 1003.1 

Systems: All


### ftell

Synopsis: 
#include <stdio.h> 
long int ftell( FILE *fp ); 

Description: The ftell function returns the current read/write position of the file specified by fp.  This position defines the character that will be read or written by the next I/O operation on the file.  The value returned by ftell can be used in a subsequent call to  fseek to set the file to the same position. 

Returns: The ftell function returns the current read/write position of the file specified by fp.  When an error is detected, -1L is returned.  When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

See Also: fgetpos, fopen, fsetpos, fseek 

Example: 
#include <stdio.h> 
long int filesize( FILE *fp ) 
 { 
  long int save_pos, size_of_file; 
  save_pos = ftell( fp ); 
  fseek( fp, 0L, SEEK_END ); 
  size_of_file = ftell( fp ); 
  fseek( fp, save_pos, SEEK_SET ); 
  return( size_of_file ); 
 } 
void main() 
 { 
  FILE *fp; 
  fp = fopen( "file", "r" ); 
  if( fp != NULL ) { 
   printf( "File size=%ld\n", filesize( fp ) ); 
   fclose( fp ); 
  } 
 } 

Classification: ANSI 

Systems: All


### ftime

Synopsis: 
#include <sys\timeb.h> 
int ftime( struct timeb *timeptr ); 
struct timeb { 
 time_t time;  /* time in seconds since Jan 1, 1970 UTC */ 
 unsigned short millitm; /* milliseconds */ 
 short timezone; /* difference in minutes from UTC */ 
 short dstflag;  /* nonzero if in daylight savings time */ 
}; 

Description: The ftime function gets the current time and stores it in the structure pointed to by timeptr. 

Returns: The ftime function fills in the fields of the structure pointed to by timeptr.  The ftime function returns -1 if not successful, and a non-zero value otherwise. 

See Also: asctime, clock, ctime, difftime, gmtime, localtime, mktime, strftime, time, tzset 

Example: 
#include <stdio.h> 
#include <time.h> 
#include <sys\timeb.h> 
void main() 
 { 
  struct timeb timebuf; 
  char  *tod; 
  ftime( &timebuf ); 
  tod = ctime( &timebuf.time ); 
  printf( "The time is %.19s.%hu %s", 
    tod, timebuf.millitm, &tod[20] ); 
 } 
produces the following: 
The time is Tue Dec 25 15:58:42.870 1990 

Classification: WATCOM 

Systems: All


### _fullpath

Synopsis: 
#include <stdlib.h> 
char *_fullpath( char *buffer, 
         const char *path, 
         size_t size ); 

Description: The _fullpath function returns the full pathname of the file specification in path in the specified buffer buffer of length size. 
The maximum size that might be required for buffer is  _MAX_PATH.  If the buffer provided is too small, NULL is returned and  errno is set. 
If buffer is NULL then a buffer of size  _MAX_PATH is allocated using  malloc.  This buffer may be freed using the  free function. 
If path is NULL or points to a null string ("") then the current working directory is returned in buffer. 

Returns: The _fullpath function returns a pointer to the full path specification if no error occurred.  Otherwise, NULL is returned. 

Errors: When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

ENOENT The current working directory could not be obtained. 

ENOMEM The buffer could not be allocated. 

ERANGE The buffer passed was too small. 

See Also: _makepath, _splitpath 

Example: 
#include <stdio.h> 
#include <stdlib.h> 
void main( int argc, char *argv[] ) 
 { 
  int i; 
  char buff[ PATH_MAX ]; 
  for( i = 1; i < argc; ++i ) { 
   puts( argv[i] ); 
   if( _fullpath( buff, argv[i], PATH_MAX ) ) { 
    puts( buff ); 
   } else { 
    puts( "FAIL!" ); 
   } 
  } 
 } 

Classification: WATCOM 

Systems: All


### fwrite

Synopsis: 
#include <stdio.h> 
size_t fwrite( const void *buf, 
        size_t elsize, 
        size_t nelem, 
        FILE *fp ); 

Description: The fwrite function writes nelem elements of elsize bytes each to the file specified by fp. 

Returns: The fwrite function returns the number of complete elements successfully written.  This value will be less than the requested number of elements only if a write error occurs.  When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

See Also: ferror, fopen 

Example: 
#include <stdio.h> 
struct student_data { 
  int  student_id; 
  unsigned char marks[10]; 
}; 
void main() 
 { 
  FILE *fp; 
  struct student_data std; 
  int i; 
  fp = fopen( "file", "w" ); 
  if( fp != NULL ) { 
   std.student_id = 1001; 
   for( i = 0; i < 10; i++ ) 
    std.marks[ i ] = (unsigned char) (85 + i); 
   /* write student record with marks */ 
   i = fwrite( &std, sizeof(std), 1, fp ); 
   printf( "%d record written\n", i ); 
   fclose( fp ); 
  } 
 } 

Classification: ANSI 

Systems: All


### gcvt

Synopsis: 
#include <stdlib.h> 
char *gcvt( double value, 
      int ndigits, 
      char *buffer ); 

Description: The gcvt function converts the floating-point number value into a character string and stores the result in buffer.  The parameter ndigits specifies the number of significant digits desired.  The converted number will be rounded to this position. 
If the exponent of the number is less than -4 or is greater than or equal to the number of significant digits wanted, then the number is converted into E-format, otherwise the number is formatted using F-format. 

Returns: The gcvt function returns a pointer to the string of digits. 

See Also: ecvt, fcvt, printf 

Example: 
#include <stdio.h> 
#include <stdlib.h> 
void main() 
 { 
  char buffer[80]; 
  printf( "%s\n", gcvt( -123.456789, 5, buffer ) ); 
  printf( "%s\n", gcvt( 123.456789E+12, 5, buffer ) ); 
 } 
produces the following: 
-123.46 
1.2346E+014 

Classification: WATCOM 

Systems: All


### _getactivepage

Synopsis: 
#include <graph.h> 
short _FAR _getactivepage( void ); 

Description: The _getactivepage function returns the number of the currently selected active graphics page. 
Only some combinations of video modes and hardware allow multiple pages of graphics to exist.  When multiple pages are supported, the active page may differ from the visual page.  The graphics information in the visual page determines what is displayed upon the screen.  Animation may be accomplished by alternating the visual page.  A graphics page can be constructed without affecting the screen by setting the active page to be different than the visual page. 
The number of available video pages can be determined by using the  _getvideoconfig function.  The default video page is 0. 

Returns: The _getactivepage function returns the number of the currently selected active graphics page. 

See Also: _setactivepage, _setvisualpage, _getvisualpage, _getvideoconfig 

Example: 
#include <conio.h> 
#include <graph.h> 
main() 
{ 
  int old_apage; 
  int old_vpage; 
  _setvideomode( _HRES16COLOR ); 
  old_apage = _getactivepage(); 
  old_vpage = _getvisualpage(); 
  /* draw an ellipse on page 0 */ 
  _setactivepage( 0 ); 
  _setvisualpage( 0 ); 
  _ellipse( _GFILLINTERIOR, 100, 50, 540, 150 ); 
  /* draw a rectangle on page 1 */ 
  _setactivepage( 1 ); 
  _rectangle( _GFILLINTERIOR, 100, 50, 540, 150 ); 
  getch(); 
  /* display page 1 */ 
  _setvisualpage( 1 ); 
  getch(); 
  _setactivepage( old_apage ); 
  _setvisualpage( old_vpage ); 
  _setvideomode( _DEFAULTMODE ); 
} 

Classification: PC Graphics 

Systems: DOS, QNX


### _getarcinfo

Synopsis: 
#include <graph.h> 
short _FAR _getarcinfo( struct xycoord _FAR *start_pt, 
            struct xycoord _FAR *end_pt, 
            struct xycoord _FAR *inside_pt ); 

Description: The _getarcinfo function returns information about the arc most recently drawn by the  _arc or  _pie functions.  The arguments start_pt and end_pt are set to contain the endpoints of the arc.  The argument inside_pt will contain the coordinates of a point within the pie.  The points are all specified in the view coordinate system. 
The endpoints of the arc can be used to connect other lines to the arc.  The interior point can be used to fill the pie. 

Returns: The _getarcinfo function returns a non-zero value when successful.  If the previous arc or pie was not successfully drawn, zero is returned. 

See Also: _arc, _pie 

Example: 
#include <conio.h> 
#include <graph.h> 
main() 
{ 
  struct xycoord start_pt, end_pt, inside_pt; 
  _setvideomode( _VRES16COLOR ); 
  _arc( 120, 90, 520, 390, 520, 90, 120, 390 ); 
  _getarcinfo( &start_pt, &end_pt, &inside_pt ); 
  _moveto( start_pt.xcoord, start_pt.ycoord ); 
  _lineto( end_pt.xcoord, end_pt.ycoord ); 
  getch(); 
  _setvideomode( _DEFAULTMODE ); 
} 
produces the following: 
The graphical image cannot be reproduced here. See the printed 
version of the manual. 

Classification: PC Graphics 

Systems: DOS, QNX


### _getbkcolor

Synopsis: 
#include <graph.h> 
long _FAR _getbkcolor( void ); 

Description: The _getbkcolor function returns the current background color.  In text modes, the background color controls the area behind each individual character.  In graphics modes, the background refers to the entire screen.  The default background color is 0. 

Returns: The _getbkcolor function returns the current background color. 

See Also: _setbkcolor, _remappalette 

Example: 
#include <conio.h> 
#include <graph.h> 
long colors[ 16 ] = { 
  _BLACK, _BLUE, _GREEN, _CYAN, 
  _RED, _MAGENTA, _BROWN, _WHITE, 
  _GRAY, _LIGHTBLUE, _LIGHTGREEN, _LIGHTCYAN, 
  _LIGHTRED, _LIGHTMAGENTA, _YELLOW, _BRIGHTWHITE 
}; 
main() 
{ 
  long old_bk; 
  int bk; 
  _setvideomode( _VRES16COLOR ); 
  old_bk = _getbkcolor(); 
  for( bk = 0; bk < 16; ++bk ) { 
    _setbkcolor( colors[ bk ] ); 
    getch(); 
  } 
  _setbkcolor( old_bk ); 
  _setvideomode( _DEFAULTMODE ); 
} 

Classification: PC Graphics 

Systems: DOS, QNX


### getc

Synopsis: 
#include <stdio.h> 
int getc( FILE *fp ); 

Description: The getc function gets the next character from the file designated by fp.  The character is returned as an int value.  The getc function is equivalent to  fgetc, except that it may be implemented as a macro. 

Returns: The getc function returns the next character from the input stream pointed to by fp.  If the stream is at end-of-file, the end-of-file indicator is set and getc returns  EOF.  If a read error occurs, the error indicator is set and getc returns  EOF.  When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

See Also: fgetc, fgetchar, fgets, fopen, getchar, gets, ungetc 

Example: 
#include <stdio.h> 
void main() 
 { 
  FILE *fp; 
  int c; 
  fp = fopen( "file", "r" ); 
  if( fp != NULL ) { 
   while( (c = getc( fp )) != EOF ) 
    putchar(c); 
   fclose( fp ); 
  } 
 } 

Classification: ANSI 

Systems: All


### getch

Synopsis: 
#include <conio.h> 
int getch( void ); 

Description: The getch function obtains the next available keystroke from the console.  Nothing is echoed on the screen (the function  getche will echo the keystroke, if possible).  When no keystroke is available, the function waits until a key is depressed. 
The  kbhit function can be used to determine if a keystroke is available. 

Returns: A value of EOF is returned when an error is detected; otherwise the getch function returns the value of the keystroke (or character). 
When the keystroke represents an extended function key (for example, a function key, a cursor-movement key or the ALT key with a letter or a digit), zero is returned and the next call to getch returns a value for the extended function. 

See Also: getche, kbhit, putch, ungetch 

Example: 
#include <stdio.h> 
#include <conio.h> 
void main() 
 { 
  int c; 
  printf( "Press any key\n" ); 
  c = getch(); 
  printf( "You pressed %c(%d)\n", c, c ); 
 } 

Classification: WATCOM 

Systems: All


### getchar

Synopsis: 
#include <stdio.h> 
int getchar( void ); 

Description: The getchar function is equivalent to  getc with the argument  stdin. 

Returns: The getchar function returns the next character from the input stream pointed to by  stdin.  If the stream is at end-of-file, the end-of-file indicator is set and getchar returns  EOF.  If a read error occurs, the error indicator is set and getchar returns  EOF.  When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

See Also: fgetc, fgetchar, getc 

Example: 
#include <stdio.h> 
void main() 
 { 
  FILE *fp; 
  int c; 
  fp = freopen( "file", "r", stdin ); 
  while( (c = getchar()) != EOF ) 
   putchar(c); 
  fclose( fp ); 
 } 

Classification: ANSI 

Systems: All


### getche

Synopsis: 
#include <conio.h> 
int getche( void ); 

Description: The getche function obtains the next available keystroke from the console.  The function will wait until a keystroke is available.  That character is echoed on the screen at the position of the cursor (use  getch when it is not desired to echo the keystroke). 
The  kbhit function can be used to determine if a keystroke is available. 

Returns: A value of EOF is returned when an error is detected; otherwise, the getche function returns the value of the keystroke (or character). 
When the keystroke represents an extended function key (for example, a function key, a cursor-movement key or the ALT key with a letter or a digit), zero is returned and the next call to getche returns a value for the extended function. 

See Also: getch, kbhit, putch, ungetch 

Example: 
#include <stdio.h> 
#include <conio.h> 
void main() 
 { 
  int c; 
  printf( "Press any key\n" ); 
  c = getche(); 
  printf( "You pressed %c(%d)\n", c, c ); 
 } 

Classification: WATCOM 

Systems: All


### _getcliprgn

Synopsis: 
#include <graph.h> 
void _FAR _getcliprgn( short _FAR *x1, short _FAR *y1, 
            short _FAR *x2, short _FAR *y2 ); 

Description: The _getcliprgn function returns the location of the current clipping region.  A clipping region is defined with the  _setcliprgn or  _setviewport functions.  By default, the clipping region is the entire screen. 
The current clipping region is a rectangular area of the screen to which graphics output is restricted.  The top left corner of the clipping region is placed in the arguments (x1,y1).  The bottom right corner of the clipping region is placed in (x2,y2). 

Returns: The _getcliprgn function returns the location of the current clipping region. 

See Also: _setcliprgn, _setviewport 

Example: 
#include <conio.h> 
#include <graph.h> 
main() 
{ 
  short x1, y1, x2, y2; 
  _setvideomode( _VRES16COLOR ); 
  _getcliprgn( &x1, &y1, &x2, &y2 ); 
  _setcliprgn( 130, 100, 510, 380 ); 
  _ellipse( _GBORDER, 120, 90, 520, 390 ); 
  getch(); 
  _setcliprgn( x1, y1, x2, y2 ); 
  _setvideomode( _DEFAULTMODE ); 
} 

Classification: PC Graphics 

Systems: DOS, QNX


### getcmd

Synopsis: 
#include <process.h> 
char *getcmd( char *cmd_line ); 

Description: The getcmd function causes the command line information, with the program name removed, to be copied to cmd_line.  The information is terminated with a '\0' character.  This provides a method of obtaining the original parameters to a program unchanged (with the white space intact). 
This information can also be obtained by examining the vector of program parameters passed to the main function in the program. 

Returns: The address of the target cmd_line is returned. 

See Also: abort, atexit, _bgetcmd, exec Functions, exit, _exit, getenv, main, onexit, putenv, spawn Functions, system 

Example: 
Suppose a program were invoked with the command line 
    
   myprog arg-1 ( my  stuff ) here 
where that program contains 
#include <stdio.h> 
#include <process.h> 
void main() 
 { 
  char cmds[128]; 
  printf( "%s\n", getcmd( cmds ) ); 
 } 
produces the following: 
 arg-1 ( my  stuff ) here 

Classification: WATCOM 

Systems: All


### _getcolor

Synopsis: 
#include <graph.h> 
short _FAR _getcolor( void ); 

Description: The _getcolor function returns the pixel value for the current color.  This is the color used for displaying graphics output.  The default color value is one less than the maximum number of colors in the current video mode. 

Returns: The _getcolor function returns the pixel value for the current color. 

See Also: _setcolor 

Example: 
#include <conio.h> 
#include <graph.h> 
main() 
{ 
  int col, old_col; 
  _setvideomode( _VRES16COLOR ); 
  old_col = _getcolor(); 
  for( col = 0; col < 16; ++col ) { 
    _setcolor( col ); 
    _rectangle( _GFILLINTERIOR, 100, 100, 540, 380 ); 
    getch(); 
  } 
  _setcolor( old_col ); 
  _setvideomode( _DEFAULTMODE ); 
} 

Classification: PC Graphics 

Systems: DOS, QNX


### _getcurrentposition, _getcurrentposition_w

Synopsis: 
#include <graph.h> 
struct xycoord _FAR _getcurrentposition( void ); 
struct _wxycoord _FAR _getcurrentposition_w( void ); 

Description: The _getcurrentposition functions return the current output position for graphics.  The _getcurrentposition function returns the point in view coordinates.  The _getcurrentposition_w function returns the point in window coordinates. 
The current position defaults to the origin, (0,0), when a new video mode is selected.  It is changed by successful calls to the  _arc,  _moveto and  _lineto functions as well as the  _setviewport function. 
Note that the output position for graphics output differs from that for text output.  The output position for text output can be set by use of the  _settextposition function. 

Returns: The _getcurrentposition functions return the current output position for graphics. 

See Also: _moveto, _settextposition 

Example: 
#include <conio.h> 
#include <graph.h> 
main() 
{ 
  struct xycoord old_pos; 
  _setvideomode( _VRES16COLOR ); 
  old_pos = _getcurrentposition(); 
  _moveto( 100, 100 ); 
  _lineto( 540, 100 ); 
  _lineto( 320, 380 ); 
  _lineto( 100, 100 ); 
  _moveto( old_pos.xcoord, old_pos.ycoord ); 
  getch(); 
  _setvideomode( _DEFAULTMODE ); 
} 

Classification: PC Graphics 

Systems:  _getcurrentposition - DOS, QNX 
_getcurrentposition_w - DOS, QNX


### getcwd

Synopsis: 
#include <direct.h> 
char *getcwd( char *buffer, int size ); 

Description: The getcwd function returns the name of the current working directory.  The buffer address is either NULL or is the location at which a string containing the name of the current working directory is placed.  In the latter case, the value of size is the length (including the delimiting '\0' character) which can be be used to store this name. 
The maximum size that might be required for buff is  PATH_MAX + 1 bytes. 
Extension:  When buffer has a value of NULL, a string is allocated to contain the name of the current working directory.  This string may be freed using the  free function. 

Returns: The getcwd function returns the address of the string containing the name of the current working directory, unless an error occurs, in which case NULL is returned. 

Errors: When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

EINVAL The argument size is negative. 

ENOMEM Not enough memory to allocate a buffer. 

ERANGE The buffer is too small (specified by size) to contain the name of the current working directory. 

See Also: chdir, mkdir, rmdir 

Example: 
#include <stdio.h> 
#include <stdlib.h> 
#include <direct.h> 
void main() 
 { 
  char *cwd; 
  cwd = getcwd( NULL, 0 ); 
  if( cwd != NULL ) { 
   printf( "My working directory is %s\n", cwd ); 
   free( cwd ); 
  } 
 } 
produces the following: 
My working directory is C:\PROJECT\C 

Classification: POSIX 1003.1 with extensions 

Systems: All


### getenv

Synopsis: 
#include <stdlib.h> 
char *getenv( const char *name ); 

Description: The getenv function searches the environment list for an entry matching the string pointed to by name.  The matching is case-insensitive; all lowercase letters are treated as if they were in upper case. 
Entries can be added to the environment list with the DOS set command or with the  putenv or  setenv functions.  All entries in the environment list can be displayed by using the DOS set command with no arguments. 
To assign a string to a variable and place it in the environment list: 
    
     C>SET INCLUDE=C:\WATCOM\H 
To see what variables are in the environment list, and their current assignments: 
    
     C>SET 
     COMSPEC=C:\COMMAND.COM 
     PATH=C:\;C:\WATCOM 
     INCLUDE=C:\WATCOM\H 

Returns: The getenv function returns a pointer to the string assigned to the environment variable if found, and NULL if no match was found.  Note:  the value returned should be duplicated if you intend to modify the contents of the string. 

See Also: clearenv, exec Functions, putenv, _searchenv, setenv, spawn Functions, system 

Example: 
#include <stdio.h> 
#include <stdlib.h> 
void main() 
 { 
  char *path; 
  path = getenv( "INCLUDE" ); 
  if( path != NULL ) 
   printf( "INCLUDE=%s\n", path ); 
 } 

Classification: ANSI 

Systems: All


### _getfillmask

Synopsis: 
#include <graph.h> 
unsigned char _FAR * _FAR 
  _getfillmask( unsigned char _FAR *mask ); 

Description: The _getfillmask function copies the current fill mask into the area located by the argument mask.  The fill mask is used by the  _ellipse,  _floodfill,  _pie,  _polygon and  _rectangle functions that fill an area of the screen. 
The fill mask is an eight-byte array which is interpreted as a square pattern (8 by 8) of 64 bits.  Each bit in the mask corresponds to a pixel.  When a region is filled, each point in the region is mapped onto the fill mask.  When a bit from the mask is one, the pixel value of the corresponding point is set using the current plotting action with the current color; when the bit is zero, the pixel value of that point is not affected. 
When the fill mask is not set, a fill operation will set all points in the fill region to have a pixel value of the current color. 

Returns: If no fill mask has been set, NULL is returned; otherwise, the _getfillmask function returns mask. 

See Also: _floodfill, _setfillmask, _setplotaction 

Example: 
#include <conio.h> 
#include <graph.h> 
char old_mask[ 8 ]; 
char new_mask[ 8 ] = { 0x81, 0x42, 0x24, 0x18, 
            0x18, 0x24, 0x42, 0x81 }; 
main() 
{ 
  _setvideomode( _VRES16COLOR ); 
  _getfillmask( old_mask ); 
  _setfillmask( new_mask ); 
  _rectangle( _GFILLINTERIOR, 100, 100, 540, 380 ); 
  _setfillmask( old_mask ); 
  getch(); 
  _setvideomode( _DEFAULTMODE ); 
} 

Classification: PC Graphics 

Systems: DOS, QNX


### _getfontinfo

Synopsis: 
#include <graph.h> 
short _FAR _getfontinfo( struct _fontinfo _FAR *info ); 

Description: The _getfontinfo function returns information about the currently selected font.  Fonts are selected with the  _setfont function.  The font information is returned in the _fontinfo structure indicated by the argument info.  The structure contains the following fields: 

type 1 for a vector font, 0 for a bit-mapped font 

ascent distance from top of character to baseline in pixels 

pixwidth character width in pixels (0 for a proportional font) 

pixheight character height in pixels 

avgwidth average character width in pixels 

filename name of the file containing the current font 

facename name of the current font 

Returns: The _getfontinfo function returns zero if the font information is returned successfully; otherwise a negative value is returned. 

See Also: _registerfonts, _unregisterfonts, _setfont, _outgtext, _getgtextextent, _setgtextvector, _getgtextvector 

Example: 
#include <conio.h> 
#include <graph.h> 
main() 
{ 
  int width; 
  struct _fontinfo info; 
  _setvideomode( _VRES16COLOR ); 
  _getfontinfo( &info ); 
  _moveto( 100, 100 ); 
  _outgtext( "WATCOM Graphics" ); 
  width = _getgtextextent( "WATCOM Graphics" ); 
  _rectangle( _GBORDER, 100, 100, 
        100 + width, 100 + info.pixheight ); 
  getch(); 
  _setvideomode( _DEFAULTMODE ); 
} 

Classification: PC Graphics 

Systems: DOS, QNX


### _getgtextextent

Synopsis: 
#include <graph.h> 
short _FAR _getgtextextent( char _FAR *text ); 

Description: The _getgtextextent function returns the length in pixels of the argument text as it would be displayed in the current font by the function  _outgtext.  Note that the text is not displayed on the screen, only its length is determined. 

Returns: The _getgtextextent function returns the length in pixels of a string. 

See Also: _registerfonts, _unregisterfonts, _setfont, _getfontinfo, _outgtext, _setgtextvector, _getgtextvector 

Example: 
#include <conio.h> 
#include <graph.h> 
main() 
{ 
  int width; 
  struct _fontinfo info; 
  _setvideomode( _VRES16COLOR ); 
  _getfontinfo( &info ); 
  _moveto( 100, 100 ); 
  _outgtext( "WATCOM Graphics" ); 
  width = _getgtextextent( "WATCOM Graphics" ); 
  _rectangle( _GBORDER, 100, 100, 
        100 + width, 100 + info.pixheight ); 
  getch(); 
  _setvideomode( _DEFAULTMODE ); 
} 

Classification: PC Graphics 

Systems: DOS, QNX


### _getgtextvector

Synopsis: 
#include <graph.h> 
struct xycoord _FAR _getgtextvector( void ); 

Description: The _getgtextvector function returns the current value of the text orientation vector.  This is the direction used when text is displayed by the  _outgtext function. 

Returns: The _getgtextvector function returns, as an xycoord structure, the current value of the text orientation vector. 

See Also: _registerfonts, _unregisterfonts, _setfont, _getfontinfo, _outgtext, _getgtextextent, _setgtextvector 

Example: 
#include <conio.h> 
#include <graph.h> 
main() 
{ 
  struct xycoord old_vec; 
  _setvideomode( _VRES16COLOR ); 
  old_vec = _getgtextvector(); 
  _setgtextvector( 0, -1 ); 
  _moveto( 100, 100 ); 
  _outgtext( "WATCOM Graphics" ); 
  _setgtextvector( old_vec.xcoord, old_vec.ycoord ); 
  getch(); 
  _setvideomode( _DEFAULTMODE ); 
} 

Classification: PC Graphics 

Systems: DOS, QNX


### _getimage, _getimage_w, _getimage_wxy

Synopsis: 
#include <graph.h> 
void _FAR _getimage( short x1, short y1, 
           short x2, short y2, 
           char _HUGE *image ); 
void _FAR _getimage_w( double x1, double y1, 
            double x2, double y2, 
            char _HUGE *image ); 
void _FAR _getimage_wxy( struct _wxycoord _FAR *p1, 
             struct _wxycoord _FAR *p2, 
             char _HUGE *image ); 

Description: The _getimage functions store a copy of an area of the screen into the buffer indicated by the image argument.  The _getimage function uses the view coordinate system.  The _getimage_w and _getimage_wxy functions use the window coordinate system. 
The screen image is the rectangular area defined by the points (x1,y1) and (x2,y2).  The buffer image must be large enough to contain the image (the size of the image can be determined by using the  _imagesize function).  The image may be displayed upon the screen at some later time by using the  _putimage functions. 

Returns: The _getimage functions do not return a value. 

See Also: _imagesize, _putimage 

Example: 
#include <conio.h> 
#include <graph.h> 
#include <malloc.h> 
main() 
{ 
  char *buf; 
  int y; 
  _setvideomode( _VRES16COLOR ); 
  _ellipse( _GFILLINTERIOR, 100, 100, 200, 200 ); 
  buf = malloc( _imagesize( 100, 100, 201, 201 ) ); 
  if( buf != NULL ) { 
    _getimage( 100, 100, 201, 201, buf ); 
    _putimage( 260, 200, buf, _GPSET ); 
    _putimage( 420, 100, buf, _GPSET ); 
    for( y = 100; y < 300; ) { 
      _putimage( 420, y, buf, _GXOR ); 
      y += 20; 
      _putimage( 420, y, buf, _GXOR ); 
    } 
    free( buf ); 
  } 
  getch(); 
  _setvideomode( _DEFAULTMODE ); 
} 

Classification: PC Graphics 

Systems:  _getimage - DOS, QNX 
_getimage_w - DOS, QNX 
_getimage_wxy - DOS, QNX


### _getlinestyle

Synopsis: 
#include <graph.h> 
unsigned short _FAR _getlinestyle( void ); 

Description: The _getlinestyle function returns the current line-style mask. 
The line-style mask determines the style by which lines and arcs are drawn.  The mask is treated as an array of 16 bits.  As a line is drawn, a pixel at a time, the bits in this array are cyclically tested.  When a bit in the array is 1, the pixel value for the current point is set using the current color according to the current plotting action; otherwise, the pixel value for the point is left unchanged.  A solid line would result from a value of 0xFFFF and a dashed line would result from a value of 0xF0F0 
The default line style mask is 0xFFFF 

Returns: The _getlinestyle function returns the current line-style mask. 

See Also: _lineto, _pie, _rectangle, _polygon, _setlinestyle 

Example: 
#include <conio.h> 
#include <graph.h> 
#define DASHED 0xf0f0 
main() 
{ 
  unsigned old_style; 
  _setvideomode( _VRES16COLOR ); 
  old_style = _getlinestyle(); 
  _setlinestyle( DASHED ); 
  _rectangle( _GBORDER, 100, 100, 540, 380 ); 
  _setlinestyle( old_style ); 
  getch(); 
  _setvideomode( _DEFAULTMODE ); 
} 

Classification: PC Graphics 

Systems: DOS, QNX


### _getphyscoord

Synopsis: 
#include <graph.h> 
struct xycoord _FAR _getphyscoord( short x, short y ); 

Description: The _getphyscoord function returns the physical coordinates of the position with view coordinates (x,y).  View coordinates are defined by the  _setvieworg and  _setviewport functions. 

Returns: The _getphyscoord function returns the physical coordinates, as an xycoord structure, of the given point. 

See Also: _getviewcoord, _setvieworg, _setviewport 

Example: 
#include <conio.h> 
#include <graph.h> 
#include <stdlib.h> 
main() 
{ 
  struct xycoord pos; 
  _setvideomode( _VRES16COLOR ); 
  _setvieworg( rand() % 640, rand() % 480 ); 
  pos = _getphyscoord( 0, 0 ); 
  _rectangle( _GBORDER, - pos.xcoord, - pos.ycoord, 
          639 - pos.xcoord, 479 - pos.ycoord ); 
  getch(); 
  _setvideomode( _DEFAULTMODE ); 
} 

Classification: PC Graphics 

Systems: DOS, QNX


### getpid

Synopsis: 
#include <process.h> 
int getpid(void); 

Description: The getpid function returns the process id for the current process. 

Returns: The getpid function returns the process id for the current process. 

Example: 
#include <stdio.h> 
#include <process.h> 
void main() 
 { 
  unsigned int process_id; 
  auto char filename[13]; 
  process_id = getpid(); 
  /* use this to create a unique file name */ 
  sprintf( filename, "TMP%4.4x.TMP", process_id ); 
 } 

Classification: POSIX 1003.1 

Systems: All


### _getpixel, _getpixel_w

Synopsis: 
#include <graph.h> 
short _FAR _getpixel( short x, short y ); 
short _FAR _getpixel_w( double x, double y ); 

Description: The _getpixel functions return the pixel value for the point with coordinates (x,y).  The _getpixel function uses the view coordinate system.  The _getpixel_w function uses the window coordinate system. 

Returns: The _getpixel functions return the pixel value for the given point when the point lies within the clipping region; otherwise, (-1) is returned. 

See Also: _setpixel 

Example: 
#include <conio.h> 
#include <graph.h> 
#include <stdlib.h> 
main() 
{ 
  int x, y; 
  unsigned i; 
  _setvideomode( _VRES16COLOR ); 
  _rectangle( _GBORDER, 100, 100, 540, 380 ); 
  for( i = 0; i <= 60000; ++i ) { 
    x = 101 + rand() % 439; 
    y = 101 + rand() % 279; 
    _setcolor( _getpixel( x, y ) + 1 ); 
    _setpixel( x, y ); 
  } 
  getch(); 
  _setvideomode( _DEFAULTMODE ); 
} 

Classification: PC Graphics 

Systems:  _getpixel - DOS, QNX 
_getpixel_w - DOS, QNX


### _getplotaction

Synopsis: 
#include <graph.h> 
short _FAR _getplotaction( void ); 

Description: The _getplotaction function returns the current plotting action. 
The drawing functions cause pixels to be set with a pixel value.  By default, the value to be set is obtained by replacing the original pixel value with the supplied pixel value.  Alternatively, the replaced value may be computed as a function of the original and the supplied pixel values. 
The plotting action can have one of the following values: 

_GPSET replace the original screen pixel value with the supplied pixel value 

_GAND replace the original screen pixel value with the bitwise and of the original pixel value and the supplied pixel value 

_GOR replace the original screen pixel value with the bitwise or of the original pixel value and the supplied pixel value 

_GXOR replace the original screen pixel value with the bitwise exclusive-or of the original pixel value and the supplied pixel value.  Performing this operation twice will restore the original screen contents, providing an efficient method to produce animated effects. 

Returns: The _getplotaction function returns the current plotting action. 

See Also: _setplotaction 

Example: 
#include <conio.h> 
#include <graph.h> 
main() 
{ 
  int old_act; 
  _setvideomode( _VRES16COLOR ); 
  old_act = _getplotaction(); 
  _setplotaction( _GPSET ); 
  _rectangle( _GFILLINTERIOR, 100, 100, 540, 380 ); 
  getch(); 
  _setplotaction( _GXOR ); 
  _rectangle( _GFILLINTERIOR, 100, 100, 540, 380 ); 
  getch(); 
  _setplotaction( old_act ); 
  _setvideomode( _DEFAULTMODE ); 
} 

Classification: PC Graphics 

Systems: DOS, QNX


### gets

Synopsis: 
#include <stdio.h> 
char *gets( char *buf ); 

Description: The gets function gets a string of characters from the file designated by  stdin and stores them in the array pointed to by buf until end-of-file is encountered or a new-line character is read.  Any new-line character is discarded, and a null character is placed immediately after the last character read into the array. 
It is recommended that  fgets be used instead of  gets because data beyond the array buf will be destroyed if a new-line character is not read from the input stream  stdin before the end of the array buf is reached. 
A common programming error is to assume the presence of a new-line character in every string that is read into the array.  A new-line character may not appear as the last character in a file, just before end-of-file. 

Returns: The gets function returns buf if successful.  NULL is returned if end-of-file is encountered, or if a read error occurs.  When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

See Also: fopen, getc, fgetc, fgets, ungetc 

Example: 
#include <stdio.h> 
void main() 
 { 
  char buffer[80]; 
  while( gets( buffer ) != NULL ) 
   puts( buffer ); 
 } 

Classification: ANSI 

Systems: All


### _gettextcolor

Synopsis: 
#include <graph.h> 
short _FAR _gettextcolor( void ); 

Description: The _gettextcolor function returns the pixel value of the current text color.  This is the color used for displaying text with the  _outtext and  _outmem functions.  The default text color value is set to 7 whenever a new video mode is selected. 

Returns: The _gettextcolor function returns the pixel value of the current text color. 

See Also: _settextcolor, _setcolor, _outtext, _outmem 

Example: 
#include <conio.h> 
#include <graph.h> 
main() 
{ 
  int old_col; 
  long old_bk; 
  _setvideomode( _TEXTC80 ); 
  old_col = _gettextcolor(); 
  old_bk = _getbkcolor(); 
  _settextcolor( 7 ); 
  _setbkcolor( _BLUE ); 
  _outtext( " WATCOM \nGraphics" ); 
  _settextcolor( old_col ); 
  _setbkcolor( old_bk ); 
  getch(); 
  _setvideomode( _DEFAULTMODE ); 
} 

Classification: PC Graphics 

Systems: DOS, QNX


### _gettextcursor

Synopsis: 
#include <graph.h> 
short _FAR _gettextcursor( void ); 

Description: The _gettextcursor function returns the current cursor attribute, or shape.  The cursor shape is set with the  _settextcursor function.  See the  _settextcursor function for a description of the value returned by the _gettextcursor function. 

Returns: The _gettextcursor function returns the current cursor shape when successful; otherwise, (-1) is returned. 

See Also: _settextcursor, _displaycursor 

Example: 
#include <conio.h> 
#include <graph.h> 
main() 
{ 
  int old_shape; 
  old_shape = _gettextcursor(); 
  _settextcursor( 0x0007 ); 
  _outtext( "\nBlock cursor" ); 
  getch(); 
  _settextcursor( 0x0407 ); 
  _outtext( "\nHalf height cursor" ); 
  getch(); 
  _settextcursor( 0x2000 ); 
  _outtext( "\nNo cursor" ); 
  getch(); 
  _settextcursor( old_shape ); 
} 

Classification: PC Graphics 

Systems: DOS, QNX


### _gettextextent

Synopsis: 
#include <graph.h> 
void _FAR _gettextextent( short x, short y, 
             char _FAR *text, 
             struct xycoord _FAR *concat, 
             struct xycoord _FAR *extent ); 

Description: The _gettextextent function simulates the effect of using the  _grtext function to display the text string text at the position (x,y), using the current text settings.  The concatenation point is returned in the argument concat.  The text extent parallelogram is returned in the array extent. 
The concatenation point is the position to use to output text after the given string.  The text extent parallelogram outlines the area where the text string would be displayed.  The four points are returned in counter-clockwise order, starting at the upper-left corner. 

Returns: The _gettextextent function does not return a value. 

See Also: _grtext, _gettextsettings 

Example: 
#include <conio.h> 
#include <graph.h> 
main() 
{ 
  struct xycoord concat; 
  struct xycoord extent[ 4 ]; 
  _setvideomode( _VRES16COLOR ); 
  _grtext( 100, 100, "hot" ); 
  _gettextextent( 100, 100, "hot", Concatenation Functions, &extent ); 
  _polygon( _GBORDER, 4, &extent ); 
  _grtext( concat.xcoord, concat.ycoord, "dog" ); 
  getch(); 
  _setvideomode( _DEFAULTMODE ); 
} 
produces the following: 
The graphical image cannot be reproduced here. See the printed 
version of the manual. 

Classification: PC Graphics 

Systems: DOS, QNX


### _gettextposition

Synopsis: 
#include <graph.h> 
struct rccoord _FAR _gettextposition( void ); 

Description: The _gettextposition function returns the current output position for text.  This position is in terms of characters, not pixels. 
The current position defaults to the top left corner of the screen, (1,1), when a new video mode is selected.  It is changed by successful calls to the  _outtext,  _outmem,  _settextposition and  _settextwindow functions. 
Note that the output position for graphics output differs from that for text output.  The output position for graphics output can be set by use of the  _moveto function. 

Returns: The _gettextposition function returns, as an rccoord structure, the current output position for text. 

See Also: _outtext, _outmem, _settextposition, _settextwindow, _moveto 

Example: 
#include <conio.h> 
#include <graph.h> 
main() 
{ 
  struct rccoord old_pos; 
  _setvideomode( _TEXTC80 ); 
  old_pos = _gettextposition(); 
  _settextposition( 10, 40 ); 
  _outtext( "WATCOM Graphics" ); 
  _settextposition( old_pos.row, old_pos.col ); 
  getch(); 
  _setvideomode( _DEFAULTMODE ); 
} 

Classification: PC Graphics 

Systems: DOS, QNX


### _gettextsettings

Synopsis: 
#include <graph.h> 
struct textsettings _FAR * _FAR _gettextsettings 
  ( struct textsettings _FAR *settings ); 

Description: The _gettextsettings function returns information about the current text settings used when text is displayed by the  _grtext function.  The information is stored in the textsettings structure indicated by the argument settings.  The structure contains the following fields (all are short fields): 

basevectorx x-component of the current base vector 

basevectory y-component of the current base vector 

path current text path 

height current text height (in pixels) 

width current text width (in pixels) 

spacing current text spacing (in pixels) 

horizalign horizontal component of the current text alignment 

vertalign vertical component of the current text alignment 

Returns: The _gettextsettings function returns information about the current graphics text settings. 

See Also: _grtext, _setcharsize, _setcharspacing, _settextalign, _settextpath, _settextorient 

Example: 
#include <conio.h> 
#include <graph.h> 
main() 
{ 
  struct textsettings ts; 
  _setvideomode( _VRES16COLOR ); 
  _gettextsettings( &ts ); 
  _grtext( 100, 100, "WATCOM" ); 
  _setcharsize( 2 * ts.height, 2 * ts.width ); 
  _grtext( 100, 300, "Graphics" ); 
  _setcharsize( ts.height, ts.width ); 
  getch(); 
  _setvideomode( _DEFAULTMODE ); 
} 

Classification: PC Graphics 

Systems: DOS, QNX


### _gettextwindow

Synopsis: 
#include <graph.h> 
void _FAR _gettextwindow( 
        short _FAR *row1, short _FAR *col1, 
        short _FAR *row2, short _FAR *col2 ); 

Description: The _gettextwindow function returns the location of the current text window.  A text window is defined with the  _settextwindow function.  By default, the text window is the entire screen. 
The current text window is a rectangular area of the screen.  Text display is restricted to be within this window.  The top left corner of the text window is placed in the arguments (row1,col1).  The bottom right corner of the text window is placed in (row2,col2). 

Returns: The _gettextwindow function returns the location of the current text window. 

See Also: _settextwindow, _outtext, _outmem, _settextposition, _scrolltextwindow 

Example: 
#include <conio.h> 
#include <graph.h> 
#include <stdio.h> 
main() 
{ 
  int i; 
  short r1, c1, r2, c2; 
  char buf[ 80 ]; 
  _setvideomode( _TEXTC80 ); 
  _gettextwindow( &r1, &c1, &r2, &c2 ); 
  _settextwindow( 5, 20, 20, 40 ); 
  for( i = 1; i <= 20; ++i ) { 
    sprintf( buf, "Line %d\n", i ); 
    _outtext( buf ); 
  } 
  getch(); 
  _settextwindow( r1, c1, r2, c2 ); 
  _setvideomode( _DEFAULTMODE ); 
} 

Classification: PC Graphics 

Systems: DOS, QNX


### _getvideoconfig

Synopsis: 
#include <graph.h> 
struct videoconfig _FAR * _FAR _getvideoconfig 
  ( struct videoconfig _FAR *config ); 

Description: The _getvideoconfig function returns information about the current video mode and the hardware configuration.  The information is returned in the videoconfig structure indicated by the argument config.  The structure contains the following fields (all are short fields): 

numxpixels number of pixels in x-axis 

numypixels number of pixels in y-axis 

numtextcols number of text columns 

numtextrows number of text rows 

numcolors number of actual colors 

bitsperpixel number of bits in a pixel value 

numvideopages number of video pages 

mode current video mode 

adapter adapter type 

monitor monitor type 

memory number of kilobytes (1024 characters) of video memory 
The adapter field will contain one of the following values: 

_NODISPLAY no display adapter attached 

_UNKNOWN unknown adapter/monitor type 

_MDPA Monochrome Display/Printer Adapter 

_CGA Color Graphics Adapter 

_HERCULES Hercules Monochrome Adapter 

_MCGA Multi-Color Graphics Array 

_EGA Enhanced Graphics Adapter 

_VGA Video Graphics Array 

_SVGA SuperVGA Adapter 
The monitor field will contain one of the following values: 

_MONO regular monochrome 

_COLOR regular color 

_ENHANCED enhanced color 

_ANALOGMONO analog monochrome 

_ANALOGCOLOR analog color 
The amount of memory reported by _getvideoconfig will not always be correct for SuperVGA adapters.  Since it is not always possible to determine the amount of memory, _getvideoconfig will always report 256K, the minimum amount. 

Returns: The _getvideoconfig function returns information about the current video mode and the hardware configuration. 

See Also: _setvideomode, _setvideomoderows 

Example: 
#include <conio.h> 
#include <graph.h> 
#include <stdio.h> 
#include <stdlib.h> 
main() 
{ 
  int mode; 
  struct videoconfig vc; 
  char buf[ 80 ]; 
  _getvideoconfig( &vc ); 
  /* select "best" video mode */ 
  switch( vc.adapter ) { 
  case _VGA : 
  case _SVGA : 
    mode = _VRES16COLOR; 
    break; 
  case _MCGA : 
    mode = _MRES256COLOR; 
    break; 
  case _EGA : 
    if( vc.monitor == _MONO ) { 
      mode = _ERESNOCOLOR; 
    } else { 
      mode = _ERESCOLOR; 
    } 
    break; 
  case _CGA : 
    mode = _MRES4COLOR; 
    break; 
  case _HERCULES : 
    mode = _HERCMONO; 
    break; 
  default : 
    puts( "No graphics adapter" ); 
    exit( 1 ); 
  } 
  if( _setvideomode( mode ) ) { 
    _getvideoconfig( &vc ); 
    sprintf( buf, "%d x %d x %d\n", vc.numxpixels, 
             vc.numypixels, vc.numcolors ); 
    _outtext( buf ); 
    getch(); 
    _setvideomode( _DEFAULTMODE ); 
  } 
} 

Classification: PC Graphics 

Systems: DOS, QNX


### _getviewcoord, _getviewcoord_w, _getviewcoord_wxy

Synopsis: 
#include <graph.h> 
struct xycoord _FAR _getviewcoord( short x, short y ); 
struct xycoord _FAR _getviewcoord_w( double x, double y ); 
struct xycoord _FAR _getviewcoord_wxy( 
          struct _wxycoord _FAR *p ); 

Description: The _getviewcoord functions translate a point from one coordinate system to viewport coordinates.  The _getviewcoord function translates the point (x,y) from physical coordinates.  The _getviewcoord_w and _getviewcoord_wxy functions translate the point from the window coordinate system. 
Viewport coordinates are defined by the  _setvieworg and  _setviewport functions.  Window coordinates are defined by the  _setwindow function. 
Note:  In previous versions of the software, the _getviewcoord function was called _getlogcoord. 

Returns: The _getviewcoord functions return the viewport coordinates, as an xycoord structure, of the given point. 

See Also: _getphyscoord, _setvieworg, _setviewport, _setwindow 

Example: 
#include <conio.h> 
#include <graph.h> 
#include <stdlib.h> 
main() 
{ 
  struct xycoord pos1, pos2; 
  _setvideomode( _VRES16COLOR ); 
  _setvieworg( rand() % 640, rand() % 480 ); 
  pos1 = _getviewcoord( 0, 0 ); 
  pos2 = _getviewcoord( 639, 479 ); 
  _rectangle( _GBORDER, pos1.xcoord, pos1.ycoord, 
             pos2.xcoord, pos2.ycoord ); 
  getch(); 
  _setvideomode( _DEFAULTMODE ); 
} 

Classification: PC Graphics 

Systems:  _getviewcoord - DOS, QNX 
_getviewcoord_w - DOS, QNX 
_getviewcoord_wxy - DOS, QNX


### _getvisualpage

Synopsis: 
#include <graph.h> 
short _FAR _getvisualpage( void ); 

Description: The _getvisualpage function returns the number of the currently selected visual graphics page. 
Only some combinations of video modes and hardware allow multiple pages of graphics to exist.  When multiple pages are supported, the active page may differ from the visual page.  The graphics information in the visual page determines what is displayed upon the screen.  Animation may be accomplished by alternating the visual page.  A graphics page can be constructed without affecting the screen by setting the active page to be different than the visual page. 
The number of available video pages can be determined by using the  _getvideoconfig function.  The default video page is 0. 

Returns: The _getvisualpage function returns the number of the currently selected visual graphics page. 

See Also: _setvisualpage, _setactivepage, _getactivepage, _getvideoconfig 

Example: 
#include <conio.h> 
#include <graph.h> 
main() 
{ 
  int old_apage; 
  int old_vpage; 
  _setvideomode( _HRES16COLOR ); 
  old_apage = _getactivepage(); 
  old_vpage = _getvisualpage(); 
  /* draw an ellipse on page 0 */ 
  _setactivepage( 0 ); 
  _setvisualpage( 0 ); 
  _ellipse( _GFILLINTERIOR, 100, 50, 540, 150 ); 
  /* draw a rectangle on page 1 */ 
  _setactivepage( 1 ); 
  _rectangle( _GFILLINTERIOR, 100, 50, 540, 150 ); 
  getch(); 
  /* display page 1 */ 
  _setvisualpage( 1 ); 
  getch(); 
  _setactivepage( old_apage ); 
  _setvisualpage( old_vpage ); 
  _setvideomode( _DEFAULTMODE ); 
} 

Classification: PC Graphics 

Systems: DOS, QNX


### _getwindowcoord

Synopsis: 
#include <graph.h> 
struct _wxycoord _FAR _getwindowcoord( short x, short y ); 

Description: The _getwindowcoord function returns the window coordinates of the position with view coordinates (x,y).  Window coordinates are defined by the  _setwindow function. 

Returns: The _getwindowcoord function returns the window coordinates, as a _wxycoord structure, of the given point. 

See Also: _setwindow, _getviewcoord 

Example: 
#include <conio.h> 
#include <graph.h> 
main() 
{ 
  struct xycoord centre; 
  struct _wxycoord pos1, pos2; 
  /* draw a box 50 pixels square */ 
  /* in the middle of the screen */ 
  _setvideomode( _MAXRESMODE ); 
  centre = _getviewcoord_w( 0.5, 0.5 ); 
  pos1 = _getwindowcoord( centre.xcoord - 25, 
              centre.ycoord - 25 ); 
  pos2 = _getwindowcoord( centre.xcoord + 25, 
              centre.ycoord + 25 ); 
  _rectangle_wxy( _GBORDER, &pos1, &pos2 ); 
  getch(); 
  _setvideomode( _DEFAULTMODE ); 
} 

Classification: PC Graphics 

Systems: DOS, QNX


### gmtime Functions

Synopsis: 
#include <time.h> 
struct tm * gmtime( const time_t *timer ); 
struct tm *_gmtime( const time_t *timer, 
          struct tm *tmbuf ); 
struct  tm { 
 int tm_sec;  /* seconds after the minute -- [0,61] */ 
 int tm_min;  /* minutes after the hour  -- [0,59] */ 
 int tm_hour;  /* hours after midnight   -- [0,23] */ 
 int tm_mday;  /* day of the month     -- [1,31] */ 
 int tm_mon;  /* months since January   -- [0,11] */ 
 int tm_year;  /* years since 1900          */ 
 int tm_wday;  /* days since Sunday     -- [0,6]  */ 
 int tm_yday;  /* days since January 1   -- [0,365]*/ 
 int tm_isdst; /* Daylight Savings Time flag */ 
}; 

Description: The gmtime functions convert the calendar time pointed to by timer into a broken-down time, expressed as Coordinated Universal Time (UTC) (formerly known as Greenwich Mean Time (GMT)). 
The function  _gmtime places the converted time in the  tm structure pointed to by tmbuf, and the function  gmtime places the converted time in a static structure that is re-used each time  gmtime is called. 
The time set on the computer with the DOS time command and the DOS date command reflects the local time.  The environment variable TZ is used to establish the time zone to which this local time applies.  See the section The TZ Environment Variable for a discussion of how to set the time zone. 

Returns: The gmtime functions return a pointer to a structure containing the broken-down time. 

See Also: asctime, clock, ctime, difftime, localtime, mktime, strftime, time, tzset 

Example: 
#include <stdio.h> 
#include <time.h> 
void main() 
 { 
  time_t time_of_day; 
  auto char buf[26]; 
  auto struct tm tmbuf; 
  time_of_day = time( NULL ); 
  _gmtime( &time_of_day, &tmbuf ); 
  printf( "It is now: %.24s GMT\n", 
      _asctime( &tmbuf, buf ) ); 
 } 
produces the following: 
It is now: Fri Dec 25 15:58:27 1987 GMT 

Classification: gmtime is ANSI, _gmtime is not ANSI 

Systems:  gmtime - All 
_gmtime - All


### _grow_handles

Synopsis: 
#include <stdio.h> 
int _grow_handles( int new_count ); 

Description: The _grow_handles function increases the number of POSIX level files that are allowed to be open at one time.  The parameter new_count is the new requested number of files that are allowed to be opened.  The return value is the number that is allowed to be opened after the call.  This may be less than, equal to, or greater than the number requested.  If the number is less than, an error has occurred and the errno variable should be consulted for the reason.  If the number returned is greater than or equal to the number requested, the call was successful. 
Note that even if _grow_handles returns successfully, you still might not be able to open the requested number of files due to some system limit (e.g.  FILES= in the CONFIG.SYS file under DOS) or because some file handles are already in use (stdin, stdout, stderr, etc.). 

Returns: The _grow_handles function returns the new number of file handles which may be open simultaneously. 

Errors: When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

See Also: fdopen, fopen, open, tmpfile 

Example: 
#include <stdio.h> 
FILE *fp[ 50 ]; 
void main() 
 { 
  int hndl_count; 
  int i; 
  hndl_count = _NFILES; 
  if( hndl_count < 50 ) { 
    hndl_count = _grow_handles( 50 ); 
  } 
  for( i = 0; i < hndl_count; i++ ) { 
   fp[ i ] = tmpfile(); 
   if( fp[ i ] == NULL ) break; 
   printf( "File %d successfully opened\n", i ); 
  } 
  printf( "%d files were successfully opened\n", i ); 
 } 

Classification: WATCOM 

Systems: All


### _grstatus

Synopsis: 
#include <graph.h> 
short _FAR _grstatus( void ); 

Description: The _grstatus function returns the status of the most recently called graphics library function.  The function can be called after any graphics function to determine if any errors or warnings occurred.  The function returns 0 if the previous function was successful.  Values less than 0 indicate an error occurred; values greater than 0 indicate a warning condition. 
The following values can be returned: 
    
   Constant        Value  Explanation 
   _GROK          0   no error 
   _GRERROR        -1   graphics error 
   _GRMODENOTSUPPORTED   -2   video mode not supported 
   _GRNOTINPROPERMODE   -3   function n/a in this mode 
   _GRINVALIDPARAMETER   -4   invalid parameter(s) 
   _GRINSUFFICIENTMEMORY  -5   out of memory 
   _GRFONTFILENOTFOUND   -6   can't open font file 
   _GRINVALIDFONTFILE   -7   font file has invalid format 
   _GRNOOUTPUT       1   nothing was done 
   _GRCLIPPED        2   output clipped 

Returns: The _grstatus function returns the status of the most recently called graphics library function. 

Example: 
#include <conio.h> 
#include <graph.h> 
#include <stdlib.h> 
main() 
{ 
  int x, y; 
  _setvideomode( _VRES16COLOR ); 
  while( _grstatus() == _GROK ) { 
    x = rand() % 700; 
    y = rand() % 500; 
    _setpixel( x, y ); 
  } 
  getch(); 
  _setvideomode( _DEFAULTMODE ); 
} 

Classification: PC Graphics 

Systems: DOS, QNX


### _grtext, _grtext_w

Synopsis: 
#include <graph.h> 
short _FAR _grtext( short x, short y, 
          char _FAR *text ); 
short _FAR _grtext_w( double x, double y, 
           char _FAR *text ); 

Description: The _grtext functions display a character string. The _grtext function uses the view coordinate system.  The _grtext_w function uses the window coordinate system. 
The character string text is displayed at the point (x,y).  The string must be terminated by a null character ('\0').  The text is displayed in the current color using the current text settings. 
The graphics library can display text in three different ways. 

 1.The  _outtext and  _outmem functions can be used in any video mode.  However, this variety of text can be displayed in only one size. 

 2.The  _grtext function displays text as a sequence of line segments, and can be drawn in different sizes, with different orientations and alignments. 

 3.The  _outgtext function displays text in the currently selected font.  Both bit-mapped and vector fonts are supported; the size and type of text depends on the fonts that are available. 

Returns: The _grtext functions return a non-zero value when the text was successfully drawn; otherwise, zero is returned. 

See Also: _outtext, _outmem, _outgtext, _setcharsize, _settextalign, _settextpath, _settextorient, _setcharspacing 

Example: 
#include <conio.h> 
#include <graph.h> 
main() 
{ 
  _setvideomode( _VRES16COLOR ); 
  _grtext( 200, 100, " WATCOM" ); 
  _grtext( 200, 200, "Graphics" ); 
  getch(); 
  _setvideomode( _DEFAULTMODE ); 
} 
produces the following: 
The graphical image cannot be reproduced here. See the printed 
version of the manual. 

Classification: PC Graphics 

Systems:  _grtext - DOS, QNX 
_grtext_w - DOS, QNX


### halloc

Synopsis: 
#include <malloc.h> 
void __huge *halloc( long int numb, size_t size ); 

Description: The halloc function allocates space for an array of numb objects of size bytes each and initializes each object to 0.  When the size of the array is greater than 64K bytes, then the size of an array element must be a power of 2 since an object could straddle a segment boundary. 

Returns: The halloc function returns a far pointer (of type void huge *) to the start of the allocated memory.  The NULL value is returned if there is insufficient memory available.  The NULL value is also returned if the size of the array is greater than 64K bytes and the size of an array element is not a power of 2. 

See Also: calloc Functions, _expand Functions, free Functions, hfree, malloc Functions, _msize Functions, realloc Functions, sbrk 

Example: 
#include <stdio.h> 
#include <malloc.h> 
void main() 
 { 
  long int __huge *big_buffer; 
  big_buffer = (long int __huge *) 
         halloc( 1024L, sizeof(long) ); 
  if( big_buffer == NULL ) { 
   printf( "Unable to allocate memory\n" ); 
  } else { 
   /* rest of code goes here */ 
   hfree( big_buffer );  /* deallocate */ 
  } 
 } 

Classification: WATCOM 

Systems: DOS/16, Win/16, QNX/16, OS/2 1.x(all)


### _harderr, _hardresume

Synopsis: 
#include <dos.h> 
void _harderr( int (__far *funcptr)() ); 
void _hardresume( int action ); 

Description: The _harderr routine installs a critical error handler (for INT 0x24) to handle hardware errors.  This critical error handler will call the function specified by funcptr when a critical error occurs (for example, attempting to open a file on a floppy disk when the drive door is open). The parameters to this function are as follows: 
    
   int handler( unsigned deverror, 
         unsigned errcode, 
         unsigned __far *devhdr ); 
The low-order byte of errcode can be one of the following values: 

0x00 Attempt to write to a write-protected disk 

0x01 Unknown unit 

0x02 Drive not ready 

0x03 Unknown command 

0x04 CRC error in data 

0x05 Bad drive-request structure length 

0x06 Seek error 

0x07 Unknown media type 

0x08 Sector not found 

0x09 Printer out of paper 

0x0A Write fault 

0x0B Read fault 

0x0C General failure 
The devhdr argument points to a device header control-block that contains information about the device on which the error occurred.  Your error handler may inspect the information in this control-block but must not change it. 
If the error occurred on a disk device, bit 15 of the deverror argument will be 0 and the deverror argument will indicate the following: 

bit 15 0 indicates disk error 

bit 14 not used 

bit 13 0 indicates "Ignore" response not allowed 

bit 12 0 indicates "Retry" response not allowed 

bit 11 0 indicates "Fail" response not allowed 

bit 9,10 location of error 

00 MS-DOS 

01 File Allocation Table (FAT) 

10 Directory 

11 Data area 

bit 8 0 indicates read error, 1 indicates write error 
The low-order byte of deverror indicates the drive where the error occurred; (0 = drive A, 1 = drive B, etc.). 
The handler is very restricted in the type of system calls that it can perform.  System calls 0x01 through 0x0C, and 0x59 are the only system calls allowed to be issued by the handler.  Therefore, many of the standard C run-time functions such as stream I/O and low-level I/O cannot be used by the handler.  Console I/O is allowed (eg.  cprintf, cputs). 
The handler must indicate what action to take by returning one of the following values or calling  _hardresume with one of the following values: 

_HARDERR_IGNORE Ignore the error 

_HARDERR_RETRY Retry the operation 

_HARDERR_ABORT Abort the program issuing INT 0x23 

_HARDERR_FAIL Fail the system call that is in progress (DOS 3.0 or higher) 
See The MS-DOS Encyclopedia for more detailed information on determining the type of error that has occurred. 

Returns: The _harderr routine does not return a value. 

See Also: _chain_intr, _dos_getvect, _dos_setvect 

Example: 
#include <stdio.h> 
#include <conio.h> 
#include <dos.h> 
int __far critical_error_handler( unsigned deverr, 
                 unsigned errcode, 
                 unsigned far *devhdr ) 
 { 
  cprintf( "Critical error: " ); 
  cprintf( "deverr=%4 . 4Xerrcode = % d \ r \ n " ,
       deverr ,errcode) ;
  cprintf (" devhdr=% Fp \ r \ n " ,devhdr) ;
  return (_ HARDERR _ IGNORE) ;
 }
main ( )
 {
  FILE* fp ;
  _ harderr (critical _ error _ handler) ;
  fp=fopen (" a : tmp . tmp " ," r ") ;
  printf (" fp=% p \ n " ,fp) ;
 }
producesthefollowing :
Criticalerror :deverr = 1A00errcode = 2
devhdr=0070 : 01b6
fp=0000

Classification: DOS 

Systems:  _harderr - DOS 
_hardresume - DOS


### _hdopen

Synopsis: 
#include <io.h> 
int _hdopen( int os_handle, int mode ); 

Description: The _hdopen function takes a previously opened operating system file handle specified by os_handle and opened with access and sharing specified by mode, and creates a POSIX-style file handle. 

Returns: The _hdopen function returns the new POSIX-style file handle if successful.  Otherwise, it returns -1. 

See Also: close, fdopen, open, _os_handle 

Example: 
#include <stdio.h> 
#include <dos.h> 
#include <fcntl.h> 
#include <io.h> 
void main() 
 { 
  int dos_handle; 
  int handle; 
  if( _dos_open( "file", O_RDONLY, &dos_handle ) != 0 ) { 
   printf( "Unable to open file\n" ); 
  } else { 
   handle = _hdopen( dos_handle, O_RDONLY ); 
   if( handle != -1 ) { 
    write( handle, "hello\n", 6 ); 
    close( handle ); 
   } 
  } 
 } 

Classification: WATCOM 

Systems: All


### _heapchk Functions

Synopsis: 
#include <malloc.h> 
int  _heapchk( void ); 
int _bheapchk( __segment seg ); 
int _fheapchk( void ); 
int _nheapchk( void ); 

Description: The  _heapchk functions along with  _heapset and  _heapwalk are provided for debugging heap related problems in programs. 
The  _heapchk functions perform a consistency check on the unallocated memory space or "heap".  The consistency check determines whether all the heap entries are valid.  Each function checks a particular heap, as listed below: 

_heapchk Depends on data model of the program 

_bheapchk Based heap specified by seg value;  _NULLSEG specifies all based heaps 

_fheapchk Far heap (outside the default data segment) 

_nheapchk Near heap (inside the default data segment) 
In a small data memory model, the  _heapchk function is equivalent to the  _nheapchk function; in a large data memory model, the  _heapchk function is equivalent to the  _fheapchk function. 

Returns: All four functions return one of the following manifest constants which are defined in <malloc.h>. 

_HEAPOK The heap appears to be consistent. 

_HEAPEMPTY The heap is empty. 

_HEAPBADBEGIN The heap has been damaged. 

_HEAPBADNODE The heap contains a bad node, or is damaged. 

See Also: _heapenable, _heapgrow, _heapmin, _heapset, _heapshrink, _heapwalk 

Example: 
#include <stdio.h> 
#include <malloc.h> 
void main() 
 { 
  char *buffer; 
  buffer = (char *)malloc( 80 ); 
  malloc( 1024 ); 
  free( buffer ); 
  switch( _heapchk() ) { 
  case _HEAPOK: 
   printf( "OK - heap is good\n" ); 
   break; 
  case _HEAPEMPTY: 
   printf( "OK - heap is empty\n" ); 
   break; 
  case _HEAPBADBEGIN: 
   printf( "ERROR - heap is damaged\n" ); 
   break; 
  case _HEAPBADNODE: 
   printf( "ERROR - bad node in heap\n" ); 
   break; 
  } 
 } 

Classification: WATCOM 

Systems:  _heapchk - All 
_fheapchk - DOS/16, Win/16, QNX/16, OS/2 1.x(all) 
_nheapchk - DOS, Win, QNX, OS/2 1.x, OS/2 1.x(MT), OS/2 2.x, NT 
_bheapchk - DOS/16, Win/16, QNX/16, OS/2 1.x(all)


### _heapenable

Synopsis: 
#include <malloc.h> 
int _heapenable( int enabled ); 

Description: The _heapenable function is used to control attempts by the heap allocation manager to request more memory from the operating system's memory pool.  If enabled is 0 then all further allocations which would normally go to the operating system for more memory will instead fail and return NULL.  If enabled is 1 then requests for more memory from the operating system's memory pool are re-enabled. 
This function can be used to impose a limit on the amount of system memory that is allocated by an application.  For example, if an application wishes to allocate no more than 200K bytes of memory, it could allocate 200K and immediately free it.  It can then call _heapenable to disable any further requests from the system memory pool.  After this, the application can allocate memory from the 200K pool that it has already obtained. 

Returns: The return value is the previous state of the system allocation flag. 

See Also: _heapchk, _heapgrow, _heapmin, _heapset, _heapshrink, _heapwalk 

Example: 
#include <stdio.h> 
#include <malloc.h> 
void main() 
 { 
  char *p; 
  p = malloc( 200*1024 ); 
  if( p != NULL ) free( p ); 
  _heapenable( 0 ); 
  /* 
   allocate memory from a pool that 
   has been capped at 200K 
  */ 
 } 

Classification: WATCOM 

Systems: All


### _heapgrow Functions

Synopsis: 
#include <malloc.h> 
void  _heapgrow( void ); 
void _nheapgrow( void ); 
void _fheapgrow( void ); 

Description: The  _nheapgrow function attempts to grow the near heap to the maximum size of 64K.  You will want to do this in the small data models if you are using both  malloc and  _fmalloc or  halloc.  Once a call to  _fmalloc or  halloc has been made, you may not be able to allocate any memory with  malloc unless space has been reserved for the near heap using either  malloc,  sbrk or  _nheapgrow. 
The  _fheapgrow function doesn't do anything to the heap because the far heap will be extended automatically when needed.  If the current far heap cannot be extended, then another far heap will be started. 
In a small data memory model, the _heapgrow function is equivalent to the  _nheapgrow function; in a large data memory model, the _heapgrow function is equivalent to the  _fheapgrow function. 

Returns: These functions do not return a value. 

See Also: _heapchk, _heapenable, _heapmin, _heapset, _heapshrink, _heapwalk 

Example: 
#include <stdio.h> 
#include <malloc.h> 
void main() 
 { 
  char *p, *fmt_string; 
  fmt_string = "Amount of memory available is %u\n"; 
  printf( fmt_string, _memavl() ); 
  _nheapgrow(); 
  printf( fmt_string, _memavl() ); 
  p = (char *) malloc( 2000 ); 
  printf( fmt_string, _memavl() ); 
 } 
produces the following: 
Amount of memory available is 0 
Amount of memory available is 62732 
Amount of memory available is 60730 

Classification: WATCOM 

Systems:  _heapgrow - All 
_fheapgrow - DOS/16, Win/16, QNX/16, OS/2 1.x(all) 
_nheapgrow - DOS, Win, QNX, OS/2 1.x, OS/2 1.x(MT), OS/2 2.x, NT


### _heapmin Functions

Synopsis: 
#include <malloc.h> 
int  _heapmin( void ); 
int _bheapmin( __segment seg ); 
int _fheapmin( void ); 
int _nheapmin( void ); 

Description: The  _heapmin functions attempt to shrink the specified heap to its smallest possible size by returning all free entries at the end of the heap back to the system.  This can be used to free up as much memory as possible before using the  system function or one of the  spawn functions. 
The various  _heapmin functions shrink the following heaps: 

_heapmin Depends on data model of the program 

_bheapmin Based heap specified by seg value; _NULLSEG specifies all based heaps 

_fheapmin Far heap (outside the default data segment) 

_nheapmin Near heap (inside the default data segment) 
In a small data memory model, the  _heapmin function is equivalent to the  _nheapmin function; in a large data memory model, the  _heapmin function is equivalent to the  _fheapmin function.  It is identical to the  _heapshrink function. 

Returns: These functions return zero if successful, and non-zero if some error occurred. 

See Also: _heapchk, _heapenable, _heapgrow, _heapset, _heapshrink, _heapwalk 

Example: 
#include <stdlib.h> 
#include <malloc.h> 
void main() 
 { 
  _heapmin(); 
  system( "chdir c:\\watcomc" ); 
 } 
Note the use of two adjacent backslash characters (\) within character-string constants to signify a single backslash. 

Classification: WATCOM 

Systems:  _heapmin - All 
_bheapmin - DOS/16, Win/16, QNX/16, OS/2 1.x(all) 
_fheapmin - DOS/16, Win/16, QNX/16, OS/2 1.x(all) 
_nheapmin - DOS, Win, QNX, OS/2 1.x, OS/2 1.x(MT), OS/2 2.x, NT


### _heapset Functions

Synopsis: 
#include <malloc.h> 
int  _heapset( unsigned char fill_char ); 
int _bheapset( __segment seg, unsigned char fill_char ); 
int _fheapset( unsigned char fill_char ); 
int _nheapset( unsigned char fill_char ); 

Description: The  _heapset functions along with  _heapchk and  _heapwalk are provided for debugging heap related problems in programs. 
The  _heapset functions perform a consistency check on the unallocated memory space or "heap" just as  _heapchk does, and sets the heap's free entries with the fill_char value. 
Each function checks and sets a particular heap, as listed below: 

_heapset Depends on data model of the program 

_bheapset Based heap specified by seg value; _NULLSEG specifies all based heaps 

_fheapset Far heap (outside the default data segment) 

_nheapset Near heap (inside the default data segment) 
In a small data memory model, the  _heapset function is equivalent to the  _nheapset function; in a large data memory model, the  _heapset function is equivalent to the  _fheapset function. 

Returns: The  _heapset functions return one of the following manifest constants which are defined in <malloc.h>. 

_HEAPOK The heap appears to be consistent. 

_HEAPEMPTY The heap is empty. 

_HEAPBADBEGIN The heap has been damaged. 

_HEAPBADNODE The heap contains a bad node, or is damaged. 

See Also: _heapchk, _heapenable, _heapgrow, _heapmin, _heapshrink, _heapwalk 

Example: 
#include <stdio.h> 
#include <malloc.h> 
void main() 
 { 
  int heap_status; 
  char *buffer; 
  buffer = (char *)malloc( 80 ); 
  malloc( 1024 ); 
  free( buffer ); 
  heap_status = _heapset( 0xff ); 
  switch( heap_status ) { 
  case _HEAPOK: 
   printf( "OK - heap is good\n" ); 
   break; 
  case _HEAPEMPTY: 
   printf( "OK - heap is empty\n" ); 
   break; 
  case _HEAPBADBEGIN: 
   printf( "ERROR - heap is damaged\n" ); 
   break; 
  case _HEAPBADNODE: 
   printf( "ERROR - bad node in heap\n" ); 
   break; 
  } 
 } 

Classification: WATCOM 

Systems:  _heapset - All 
_fheapset - DOS/16, Win/16, QNX/16, OS/2 1.x(all) 
_nheapset - DOS, Win, QNX, OS/2 1.x, OS/2 1.x(MT), OS/2 2.x, NT 
_bheapset - DOS/16, Win/16, QNX/16, OS/2 1.x(all)


### _heapshrink Functions

Synopsis: 
#include <malloc.h> 
int  _heapshrink( void ); 
int _bheapshrink( __segment seg ); 
int _fheapshrink( void ); 
int _nheapshrink( void ); 

Description: The  _heapshrink functions attempt to shrink the heap to its smallest possible size by returning all free entries at the end of the heap back to the system.  This can be used to free up as much memory as possible before using the  system function or one of the  spawn functions. 
The various  _heapshrink functions shrink the following heaps: 

_heapshrink Depends on data model of the program 

_bheapshrink Based heap specified by seg value;  _NULLSEG specifies all based heaps 

_fheapshrink Far heap (outside the default data segment) 

_nheapshrink Near heap (inside the default data segment) 
In a small data memory model, the  _heapshrink function is equivalent to the  _nheapshrink function; in a large data memory model, the  _heapshrink function is equivalent to the  _fheapshrink function.  It is identical to the  _heapmin function. 

Returns: These functions return zero if successful, and non-zero if some error occurred. 

See Also: _heapchk, _heapenable, _heapgrow, _heapmin, _heapset, _heapwalk 

Example: 
#include <stdlib.h> 
#include <malloc.h> 
void main() 
 { 
  _heapshrink(); 
  system( "chdir c:\\watcomc" ); 
 } 
Note the use of two adjacent backslash characters (\) within character-string constants to signify a single backslash. 

Classification: WATCOM 

Systems:  _heapshrink - All 
_bheapshrink - DOS/16, Win/16, QNX/16, OS/2 1.x(all) 
_fheapshrink - DOS/16, Win/16, QNX/16, OS/2 1.x(all) 
_nheapshrink - DOS, Win, QNX, OS/2 1.x, OS/2 1.x(MT), OS/2 2.x, NT


### _heapwalk Functions

Synopsis: 
#include <malloc.h> 
int  _heapwalk( struct _heapinfo *entry ); 
int _bheapwalk( __segment seg, struct _heapinfo *entry ); 
int _fheapwalk( struct _heapinfo *entry ); 
int _nheapwalk( struct _heapinfo *entry ); 
struct _heapinfo { 
  void __far *_pentry;  /* heap pointer */ 
  size_t   _size;    /* heap entry size */ 
  int     _useflag;  /* heap entry 'in-use' flag */ 
}; 
#define _USEDENTRY    0 
#define _FREEENTRY    1 

Description: The  _heapwalk functions along with  _heapchk and  _heapset are provided for debugging heap related problems in programs. 
The  _heapwalk functions walk through the heap, one entry per call, updating the  _heapinfo structure with information on the next heap entry.  The structure is defined in <malloc.h>.  You must initialize the _pentry field with NULL to start the walk through the heap. 
Each function walks a particular heap, as listed below: 

_heapwalk Depends on data model of the program 

_bheapwalk Based heap specified by seg value; _NULLSEG specifies all based heaps 

_fheapwalk Far heap (outside the default data segment) 

_nheapwalk Near heap (inside the default data segment) 
In a small data memory model, the  _heapwalk function is equivalent to the  _nheapwalk function; in a large data memory model, the  _heapwalk function is equivalent to the  _fheapwalk function. 

Returns: These functions return one of the following manifest constants which are defined in <malloc.h>. 

_HEAPOK The heap is OK so far, and the  _heapinfo structure contains information about the next entry in the heap. 

_HEAPEMPTY The heap is empty. 

_HEAPBADPTR The  _pentry field of the entry structure does not contain a valid pointer into the heap. 

_HEAPBADBEGIN The header information for the heap was not found or has been damaged. 

_HEAPBADNODE The heap contains a bad node, or is damaged. 

_HEAPEND The end of the heap was reached successfully. 

See Also: _heapchk, _heapenable, _heapgrow, _heapmin, _heapset, _heapshrink 

Example: 
#include <stdio.h> 
#include <malloc.h> 
heap_dump() 
 { 
  struct _heapinfo h_info; 
  int heap_status; 
  h_info._pentry = NULL; 
  for(;;) { 
   heap_status = _heapwalk( &h_info ); 
   if( heap_status != _HEAPOK ) break; 
   printf( "  %s block at %Fp of size %4.4X\n", 
    (h_info._useflag == _USEDENTRY ? "USED" : "FREE"), 
    h_info._pentry, h_info._size ); 
  } 
  switch( heap_status ) { 
  case _HEAPEND: 
   printf( "OK - end of heap\n" ); 
   break; 
  case _HEAPEMPTY: 
   printf( "OK - heap is empty\n" ); 
   break; 
  case _HEAPBADBEGIN: 
   printf( "ERROR - heap is damaged\n" ); 
   break; 
  case _HEAPBADPTR: 
   printf( "ERROR - bad pointer to heap\n" ); 
   break; 
  case _HEAPBADNODE: 
   printf( "ERROR - bad node in heap\n" ); 
  } 
 } 
void main() 
 { 
  char *p; 
  heap_dump();  p = (char *) malloc( 80 ); 
  heap_dump();  free( p ); 
  heap_dump(); 
 } 
produces the following: 
On 16-bit 80x86 systems, the following output is produced: 
OK - heap is empty 
 USED block at 23f8:0ab6 of size 0202 
 USED block at 23f8:0cb8 of size 0052 
 FREE block at 23f8:0d0a of size 1DA2 
OK - end of heap 
 USED block at 23f8:0ab6 of size 0202 
 FREE block at 23f8:0cb8 of size 1DF4 
OK - end of heap 
On 32-bit 80386/486 systems, the following output is produced: 
OK - heap is empty 
 USED block at 0014:00002a7c of size 0204 
 USED block at 0014:00002c80 of size 0054 
 FREE block at 0014:00002cd4 of size 1D98 
OK - end of heap 
 USED block at 0014:00002a7c of size 0204 
 FREE block at 0014:00002c80 of size 1DEC 
OK - end of heap 

Classification: WATCOM 

Systems:  _heapwalk - All 
_bheapwalk - DOS/16, Win/16, QNX/16, OS/2 1.x(all) 
_fheapwalk - DOS/16, Win/16, QNX/16, OS/2 1.x(all) 
_nheapwalk - DOS, Win, QNX, OS/2 1.x, OS/2 1.x(MT), OS/2 2.x, NT


### hfree

Synopsis: 
#include <malloc.h> 
void hfree( void __huge *ptr ); 

Description: The hfree function deallocates a memory block previously allocated by the  halloc function.  The argument ptr points to a memory block to be deallocated.  After the call, the freed block is available for allocation. 

Returns: The hfree function returns no value. 

See Also: calloc Functions, _expand Functions, free Functions, halloc, malloc Functions, _msize Functions, realloc Functions, sbrk 

Example: 
#include <stdio.h> 
#include <malloc.h> 
void main() 
 { 
  long int __huge *big_buffer; 
  big_buffer = (long int __huge *) 
         halloc( 1024L, sizeof(long) ); 
  if( big_buffer == NULL ) { 
   printf( "Unable to allocate memory\n" ); 
  } else { 
   /* rest of code goes here */ 
   hfree( big_buffer );  /* deallocate */ 
  } 
 } 

Classification: WATCOM 

Systems: DOS/16, Win/16, QNX/16, OS/2 1.x(all)


### hypot

Synopsis: 
#include <math.h> 
double hypot( double x, double y ); 

Description: The hypot function computes the length of the hypotenuse of a right triangle whose sides are x and y adjacent to that right angle.  The calculation is equivalent to 
  sqrt( x*x + y*y ) 
The computation may cause an overflow, in which case the  matherr function will be invoked. 

Returns: The value of the hypotenuse is returned.  When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

Example: 
#include <stdio.h> 
#include <math.h> 
void main() 
 { 
  printf( "%f\n", hypot( 3.0, 4.0 ) ); 
 } 
produces the following: 
5.000000 

Classification: WATCOM 

Systems: All


### _imagesize, _imagesize_w, _imagesize_wxy

Synopsis: 
#include <graph.h> 
long _FAR _imagesize( short x1, short y1, 
           short x2, short y2 ); 
long _FAR _imagesize_w( double x1, double y1, 
            double x2, double y2 ); 
long _FAR _imagesize_wxy( struct _wxycoord _FAR *p1, 
             struct _wxycoord _FAR *p2 ); 

Description: The _imagesize functions compute the number of bytes required to store a screen image.  The _imagesize function uses the view coordinate system.  The _imagesize_w and _imagesize_wxy functions use the window coordinate system. 
The screen image is the rectangular area defined by the points (x1,y1) and (x2,y2).  The storage area used by the  _getimage functions must be at least this large (in bytes). 

Returns: The _imagesize functions return the size of a screen image. 

See Also: _getimage, _putimage 

Example: 
#include <conio.h> 
#include <graph.h> 
#include <malloc.h> 
main() 
{ 
  char *buf; 
  int y; 
  _setvideomode( _VRES16COLOR ); 
  _ellipse( _GFILLINTERIOR, 100, 100, 200, 200 ); 
  buf = malloc( _imagesize( 100, 100, 201, 201 ) ); 
  if( buf != NULL ) { 
    _getimage( 100, 100, 201, 201, buf ); 
    _putimage( 260, 200, buf, _GPSET ); 
    _putimage( 420, 100, buf, _GPSET ); 
    for( y = 100; y < 300; ) { 
      _putimage( 420, y, buf, _GXOR ); 
      y += 20; 
      _putimage( 420, y, buf, _GXOR ); 
    } 
    free( buf ); 
  } 
  getch(); 
  _setvideomode( _DEFAULTMODE ); 
} 

Classification: PC Graphics 

Systems:  _imagesize - DOS, QNX 
_imagesize_w - DOS, QNX 
_imagesize_wxy - DOS, QNX


### inp

Synopsis: 
#include <conio.h> 
unsigned int inp( int port ); 

Description: The inp function reads one byte from the 80x86 hardware port whose number is given by port. 
A hardware port is used to communicate with a device.  One or two bytes can be read and/or written from each port, depending upon the hardware.  Consult the technical documentation for your computer to determine the port numbers for a device and the expected usage of each port for a device. 

Returns: The value returned is the byte that was read. 

See Also: inpd, inpw, outp, outpd, outpw 

Example: 
#include <conio.h> 
void main() 
 { 
  /* turn off speaker */ 
  outp( 0x61, inp( 0x61 ) & 0xFC ); 
 } 

Classification: Intel 

Systems: All


### inpd

Synopsis: 
#include <conio.h> 
unsigned long inpd( int port ); 

Description: The inpd function reads a double-word (four bytes) from the 80x86 hardware port whose number is given by port. 
A hardware port is used to communicate with a device.  One or two bytes can be read and/or written from each port, depending upon the hardware.  Consult the technical documentation for your computer to determine the port numbers for a device and the expected usage of each port for a device. 

Returns: The value returned is the double-word that was read. 

See Also: inp, inpw, outp, outpd, outpw 

Example: 
#include <conio.h> 
#define DEVICE 34 
void main() 
 { 
  unsigned long transmitted; 
  transmitted = inpd( DEVICE ); 
 } 

Classification: Intel 

Systems: DOS/32, Win/32, QNX/32, OS/2 2.x, NT


### inpw

Synopsis: 
#include <conio.h> 
unsigned int inpw( int port ); 

Description: The inpw function reads a word (two bytes) from the 80x86 hardware port whose number is given by port. 
A hardware port is used to communicate with a device.  One or two bytes can be read and/or written from each port, depending upon the hardware.  Consult the technical documentation for your computer to determine the port numbers for a device and the expected usage of each port for a device. 

Returns: The value returned is the word that was read. 

See Also: inp, inpd, outp, outpd, outpw 

Example: 
#include <conio.h> 
#define DEVICE 34 
void main() 
 { 
  unsigned int transmitted; 
  transmitted = inpw( DEVICE ); 
 } 

Classification: Intel 

Systems: All


### int386

Synopsis: 
#include <i86.h> 
int int386( int inter_no, 
      const union REGS *in_regs, 
      union REGS *out_regs ); 

Description: The int386 function causes the computer's central processor (CPU) to be interrupted with an interrupt whose number is given by inter_no.  This function is present in the 386 C libraries and may be executed on 80386/486 systems.  Before the interrupt, the CPU registers are loaded from the structure located by in_regs.  Following the interrupt, the structure located by out_regs is filled with the contents of the CPU registers.  These structures may be located at the same location in memory. 
You should consult the technical documentation for the computer that you are using to determine the expected register contents before and after the interrupt in question. 

Returns: The function returns the value of the CPU EAX register after the interrupt. 

See Also: bdos, int386x, int86, int86x, intdos, intdosx, intr, segread 

Example: 
/* 
 * This example clears the screen on DOS 
 */ 
#include <i86.h> 
void main() 
 { 
  union REGS  regs; 
  regs.w.cx = 0; 
  regs.w.dx = 0x1850; 
  regs.h.bh = 7; 
  regs.w.ax = 0x0600; 
#ifdef __386__ 
  int386( 0x10, &regs, &regs ); 
#else 
  int86( 0x10, &regs, &regs ); 
#endif 
 } 

Classification: Intel 

Systems: DOS/32, QNX/32


### int386x

Synopsis: 
#include <i86.h> 
int int386x( int inter_no, 
       const union REGS *in_regs, 
       union REGS *out_regs, 
       struct SREGS *seg_regs ); 

Description: The int386x function causes the computer's central processor (CPU) to be interrupted with an interrupt whose number is given by inter_no.  This function is present in the 32-bit C libraries and may be executed on Intel 386 compatible systems.  Before the interrupt, the CPU registers are loaded from the structure located by in_regs and the DS, ES, FS and GS segment registers are loaded from the structure located by seg_regs.  All of the segment registers must contain valid values.  Failure to do so will cause a segment violation when running in protect mode.  If you don't care about a particular segment register, then it can be set to 0 which will not cause a segment violation.  The function  segread can be used to initialize seg_regs to their current values. 
Following the interrupt, the structure located by out_regs is filled with the contents of the CPU registers.  The in_regs and out_regs structures may be located at the same location in memory.  The original values of the DS, ES, FS and GS registers are restored.  The structure seg_regs is updated with the values of the segment registers following the interrupt. 
You should consult the technical documentation for the computer that you are using to determine the expected register contents before and after the interrupt in question. 

Returns: The function returns the value of the CPU EAX register after the interrupt. 

See Also: bdos, int386, int86, int86x, intdos, intdosx, intr, segread 

Example: 
#include <stdio.h> 
#include <i86.h> 
/* get current mouse interrupt handler address */ 
void main() 
 { 
  union REGS r; 
  struct SREGS s; 
  s.ds = s.es = s.fs = s.gs = FP_SEG( &s ); 
#if defined(__PHARLAP__) 
  r.w.ax = 0x2503;   /* get real-mode vector */ 
  r.h.cl = 0x33;    /* interrupt vector 0x33 */ 
  int386( 0x21, &r, &r ); 
  printf( "mouse handler real-mode address=" 
      "%lx\n", r.x.ebx ); 
  r.w.ax = 0x2502;   /* get protected-mode vector */ 
  r.h.cl = 0x33;    /* interrupt vector 0x33 */ 
  int386x( 0x21, &r, &r, &s ); 
  printf( "mouse handler protected-mode address=" 
      "%x:%lx\n", s.es, r.x.ebx ); 
#else 
  r.h.ah = 0x35;  /* get vector */ 
  r.h.al = 0x33;  /* vector 0x33 */ 
  int386x( 0x21, &r, &r, &s ); 
  printf( "mouse handler protected-mode address=" 
      "%x:%lx\n", s.es, r.x.ebx ); 
#endif 
 } 

Classification: Intel 

Systems: DOS/32, QNX/32


### int86

Synopsis: 
#include <i86.h> 
int int86( int inter_no, 
      const union REGS *in_regs, 
      union REGS *out_regs ); 

Description: The int86 function causes the computer's central processor (CPU) to be interrupted with an interrupt whose number is given by inter_no.  Before the interrupt, the CPU registers are loaded from the structure located by in_regs.  Following the interrupt, the structure located by out_regs is filled with the contents of the CPU registers.  These structures may be located at the same location in memory. 
You should consult the technical documentation for the computer that you are using to determine the expected register contents before and after the interrupt in question. 

Returns: The function returns the value of the CPU AX register after the interrupt. 

See Also: bdos, int386, int386x, int86x, intdos, intdosx, intr, segread 

Example: 
/* 
 * This example clears the screen on DOS 
 */ 
#include <i86.h> 
void main() 
 { 
  union REGS  regs; 
  regs.w.cx = 0; 
  regs.w.dx = 0x1850; 
  regs.h.bh = 7; 
  regs.w.ax = 0x0600; 
#ifdef __386__ 
  int386( 0x10, &regs, &regs ); 
#else 
  int86( 0x10, &regs, &regs ); 
#endif 
 } 

Classification: Intel 

Systems: DOS/16, Win, QNX/16, DOS/PM


### int86x

Synopsis: 
#include <i86.h> 
int int86x( int inter_no, 
      const union REGS *in_regs, 
      union REGS *out_regs, 
      struct SREGS *seg_regs ); 

Description: The int86x function causes the computer's central processor (CPU) to be interrupted with an interrupt whose number is given by inter_no.  Before the interrupt, the CPU registers are loaded from the structure located by in_regs and the DS and ES segment registers are loaded from the structure located by seg_regs.  All of the segment registers must contain valid values.  Failure to do so will cause a segment violation when running in protect mode.  If you don't care about a particular segment register, then it can be set to 0 which will not cause a segment violation.  The function  segread can be used to initialize seg_regs to their current values. 
Following the interrupt, the structure located by out_regs is filled with the contents of the CPU registers.  The in_regs and out_regs structures may be located at the same location in memory.  The original values of the DS and ES registers are restored.  The structure seg_regs is updated with the values of the segment registers following the interrupt. 
You should consult the technical documentation for the computer that you are using to determine the expected register contents before and after the interrupt in question. 

Returns: The function returns the value of the CPU AX register after the interrupt. 

See Also: bdos, int386, int386x, int86, intdos, intdosx, intr, segread 

Example: 
#include <stdio.h> 
#include <i86.h> 
/* get current mouse interrupt handler address */ 
void main() 
 { 
  union REGS r; 
  struct SREGS s; 
  r.h.ah = 0x35;  /* DOS get vector */ 
  r.h.al = 0x33;  /* interrupt vector 0x33 */ 
  int86x( 0x21, &r, &r, &s ); 
  printf( "mouse handler address=%4.4x:%4.4x\n", 
      s.es, r.w.bx ); 
 } 

Classification: Intel 

Systems: DOS/16, Win, QNX/16, DOS/PM


### intdos

Synopsis: 
#include <dos.h> 
int intdos( const union REGS *in_regs, 
      union REGS *out_regs ); 

Description: The intdos function causes the computer's central processor (CPU) to be interrupted with an interrupt number hexadecimal 21 (0x21), which is a request to invoke a specific DOS function.  Before the interrupt, the CPU registers are loaded from the structure located by in_regs.  The AH register contains a number indicating the function requested.  Following the interrupt, the structure located by out_regs is filled with the contents of the CPU registers.  These structures may be located at the same location in memory. 
You should consult the technical documentation for the DOS operating system that you are using to determine the expected register contents before and after the interrupt in question. 

Returns: The function returns the value of the AX (EAX in 386 library) register after the interrupt has completed.  The CARRY flag (when set, an error has occurred) is copied into the structure located by out_regs.  When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

See Also: bdos, int386, int386x, int86, int86x, intdosx, intr, segread 

Example: 
#include <dos.h> 
#define DISPLAY_OUTPUT  2 
void main() 
 { 
  union REGS  in_regs, out_regs; 
  int     rc; 
  in_regs.h.ah = DISPLAY_OUTPUT; 
  in_regs.h.al = 0; 
  in_regs.w.dx = 'I'; 
  rc = intdos( &in_regs, &out_regs ); 
  in_regs.w.dx = 'N'; 
  rc = intdos( &in_regs, &out_regs ); 
  in_regs.w.dx = 'T'; 
  rc = intdos( &in_regs, &out_regs ); 
  in_regs.w.dx = 'D'; 
  rc = intdos( &in_regs, &out_regs ); 
  in_regs.w.dx = 'O'; 
  rc = intdos( &in_regs, &out_regs ); 
  in_regs.w.dx = 'S'; 
  rc = intdos( &in_regs, &out_regs ); 
 } 

Classification: DOS 

Systems: DOS, Win, DOS/PM


### intdosx

Synopsis: 
#include <dos.h> 
int intdosx( const union REGS *in_regs, 
       union REGS *out_regs, 
       struct SREGS *seg_regs ); 

Description: The intdosx function causes the computer's central processor (CPU) to be interrupted with an interrupt number hexadecimal 21 (0x21), which is a request to invoke a specific DOS function.  Before the interrupt, the CPU registers are loaded from the structure located by in_regs and the segment registers DS and ES are loaded from the structure located by seg_regs.  The AH register contains a number indicating the function requested.  All of the segment registers must contain valid values.  Failure to do so will cause a segment violation when running in protect mode.  If you don't care about a particular segment register, then it can be set to 0 which will not cause a segment violation.  The function  segread can be used to initialize seg_regs to their current values. 
Following the interrupt, the structure located by out_regs is filled with the contents of the CPU registers.  The in_regs and out_regs structures may be located at the same location in memory.  The original values for the DS and ES registers are restored.  The structure seg_regs is updated with the values of the segment registers following the interrupt. 
You should consult the technical documentation for the DOS operating system that you are using to determine the expected register contents before and after the interrupt in question. 

Returns: The function returns the value of the AX (EAX in 386 library) register after the interrupt has completed.  The CARRY flag (when set, an error has occurred) is copied into the structure located by out_regs.  When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

See Also: bdos, int386, int386x, int86, int86x, intdos, intr, segread 

Example: 
#include <stdio.h> 
#include <dos.h> 
/* get current mouse interrupt handler address */ 
void main() 
 { 
  union REGS r; 
  struct SREGS s; 
#if defined(__386__) 
  s.ds = s.es = s.fs = s.gs = FP_SEG( &s ); 
#endif 
  r.h.ah = 0x35;  /* get vector */ 
  r.h.al = 0x33;  /* vector 0x33 */ 
  intdosx( &r, &r, &s ); 
#if defined(__386__) 
  printf( "mouse handler address=%4.4x:%lx\n", 
      s.es, r.x.ebx ); 
#else 
  printf( "mouse handler address=%4.4x:%4.4x\n", 
      s.es, r.x.bx ); 
#endif 
 } 

Classification: DOS 

Systems: DOS, Win, DOS/PM


### intr

Synopsis: 
#include <i86.h> 
void intr( int inter_no, union REGPACK *regs ); 

Description: The intr function causes the computer's central processor (CPU) to be interrupted with an interrupt whose number is given by inter_no.  Before the interrupt, the CPU registers are loaded from the structure located by regs.  All of the segment registers must contain valid values.  Failure to do so will cause a segment violation when running in protect mode.  If you don't care about a particular segment register, then it can be set to 0 which will not cause a segment violation.  Following the interrupt, the structure located by regs is filled with the contents of the CPU registers. 
This function is similar to the  int86x function, except that only one structure is used for the register values and that the BP (EBP in 386 library) register is included in the set of registers that are passed and saved. 
You should consult the technical documentation for the computer that you are using to determine the expected register contents before and after the interrupt in question. 

Returns: The function does not return a value. 

See Also: bdos, int386, int386x, int86, int86x, intdos, intdosx, segread 

Example: 
#include <stdio.h> 
#include <string.h> 
#include <i86.h> 
void main() /* Print location of Break Key Vector */ 
 { 
  union REGPACK regs; 
  memset( &regs, 0, sizeof(union REGPACK) ); 
  regs.w.ax = 0x3523; 
  intr( 0x21, &regs ); 
  printf( "Break Key vector is " 
#if defined(__386__) 
      "%x:%lx\n", regs.w.es, regs.x.ebx ); 
#else 
      "%x:%x\n", regs.w.es, regs.x.bx ); 
#endif 
 } 
produces the following: 
Break Key vector is eef:13c 

Classification: Intel 

Systems: DOS, Win, QNX, DOS/PM


### isalnum

Synopsis: 
#include <ctype.h> 
int isalnum( int c ); 

Description: The isalnum function tests if the argument c is an alphanumeric character ('a' to 'z', 'A' to 'Z', or '0' to '9').  An alphanumeric character is any character for which  isalpha or  isdigit is true. 

Returns: The isalnum returns zero if the argument is neither an alphabetic character nor a digit.  Otherwise, a non-zero value is returned. 

See Also: isalpha, isdigit, islower 

Example: 
#include <stdio.h> 
#include <ctype.h> 
void main() 
 { 
  if( isalnum( getchar() ) ) { 
   printf( "is alpha-numeric\n" ); 
  } 
 } 

Classification: ANSI 

Systems: All


### isalpha

Synopsis: 
#include <ctype.h> 
int isalpha( int c ); 

Description: The isalpha function tests if the argument c is an alphabetic character ('a' to 'z' and 'A' to 'Z').  An alphabetic character is any character for which  isupper or  islower is true. 

Returns: The isalpha returns zero if the argument is not an alphabetic character otherwise, a non-zero value is returned. 

See Also: isalnum, iscntrl, isdigit, isgraph, islower, isprint, ispunct, isspace, isupper, isxdigit, tolower, toupper 

Example: 
#include <stdio.h> 
#include <ctype.h> 
void main() 
 { 
  if( isalpha( getchar() ) ) { 
   printf( "is alphabetic\n" ); 
  } 
 } 

Classification: ANSI 

Systems: All


### isascii

Synopsis: 
#include <ctype.h> 
int isascii( int c ); 

Description: The isascii function tests for a character in the range from 0 to 127. 

Returns: A non-zero value is returned when the character is in the range 0 to 127; otherwise, zero is returned. 

See Also: isalpha, isalnum, iscntrl, isdigit, isgraph, islower, isprint, ispunct, isspace, isupper, isxdigit, tolower, toupper 

Example: 
#include <stdio.h> 
#include <ctype.h> 
char chars[] = { 
  'A', 
  0x80, 
  'Z' 
}; 
#define SIZE sizeof( chars ) / sizeof( char ) 
void main() 
 { 
  int  i; 
  for( i = 0; i < SIZE; i++ ) { 
   printf( "Char %c is %san ASCII character\n", 
      chars[i], 
      ( isascii( chars[i] ) ) ? "" : "not " ); 
  } 
 } 
produces the following: 
Char A is an ASCII character 
Char  is not an ASCII character 
Char Z is an ASCII character 

Classification: WATCOM 

Systems: All


### isatty

Synopsis: 
#include <io.h> 
int isatty( int handle ); 

Description: The isatty function tests if the opened file or device referenced by the file handle handle is a character device (for example, a console, printer or port). 

Returns: The isatty function returns zero if the device or file is not a character device; otherwise, a non-zero value is returned.  When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

See Also: open 

Example: 
#include <stdio.h> 
#include <io.h> 
void main() 
 { 
  printf( "stdin is a %stty\n", 
      ( isatty( fileno( stdin ) ) ) 
      ? "" : "not " ); 
 } 

Classification: POSIX 1003.1 

Systems: All


### iscntrl

Synopsis: 
#include <ctype.h> 
int iscntrl( int c ); 

Description: The iscntrl function tests for any control character.  A control character is any character whose value is from 0 through 31. 

Returns: The iscntrl returns a non-zero value when the argument is a control character; otherwise, zero is returned. 

See Also: isalnum, isalpha, isdigit, isgraph, islower, isprint, ispunct, isspace, isupper, isxdigit, tolower, toupper 

Example: 
#include <stdio.h> 
#include <ctype.h> 
char chars[] = { 
  'A', 
  0x09, 
  'Z' 
}; 
#define SIZE sizeof( chars ) / sizeof( char ) 
void main() 
 { 
  int  i; 
  for( i = 0; i < SIZE; i++ ) { 
   printf( "Char %c is %sa Control character\n", 
      chars[i], 
      ( iscntrl( chars[i] ) ) ? "" : "not " ); 
  } 
 } 
produces the following: 
Char A is not a Control character 
Char   is a Control character 
Char Z is not a Control character 

Classification: ANSI 

Systems: All


### isdigit

Synopsis: 
#include <ctype.h> 
int isdigit( int c ); 

Description: The isdigit function tests for any decimal-digit character '0' through '9'. 

Returns: The isdigit function returns a non-zero value when the argument is a digit; otherwise, zero is returned. 

See Also: isalnum, isalpha, iscntrl, isgraph, islower, isprint, ispunct, isspace, isupper, isxdigit, tolower, toupper 

Example: 
#include <stdio.h> 
#include <ctype.h> 
char chars[] = { 
  'A', 
  '5', 
  '$' 
}; 
#define SIZE sizeof( chars ) / sizeof( char ) 
void main() 
 { 
  int  i; 
  for( i = 0; i < SIZE; i++ ) { 
   printf( "Char %c is %sa digit character\n", 
      chars[i], 
      ( isdigit( chars[i] ) ) ? "" : "not " ); 
  } 
 } 
produces the following: 
Char A is not a digit character 
Char 5 is a digit character 
Char $ is not a digit character 

Classification: ANSI 

Systems: All


### isgraph

Synopsis: 
#include <ctype.h> 
int isgraph( int c ); 

Description: The isgraph function tests for any printable character except space (' ').  The  isprint function is similar, except that the space character is also included in the character set being tested. 

Returns: The isgraph function returns non-zero when the argument is a printable character (except a space); otherwise, zero is returned. 

See Also: isalnum, isalpha, iscntrl, isdigit, islower, isprint, ispunct, isspace, isupper, isxdigit, tolower, toupper 

Example: 
#include <stdio.h> 
#include <ctype.h> 
char chars[] = { 
  'A', 
  0x09, 
  ' ', 
  0x7d 
}; 
#define SIZE sizeof( chars ) / sizeof( char ) 
void main() 
 { 
  int  i; 
  for( i = 0; i < SIZE; i++ ) { 
   printf( "Char %c is %sa printable character\n", 
      chars[i], 
      ( isgraph( chars[i] ) ) ? "" : "not " ); 
  } 
 } 
produces the following: 
Char A is a printable character 
Char   is not a printable character 
Char  is not a printable character 
Char } is a printable character 

Classification: ANSI 

Systems: All


### islower

Synopsis: 
#include <ctype.h> 
int islower( int c ); 

Description: The islower function tests for any lowercase letter 'a' through 'z'. 

Returns: The islower function returns a non-zero value when argument is a lowercase letter; otherwise, zero is returned. 

See Also: isalnum, isalpha, iscntrl, isdigit, isgraph, isprint, ispunct, isspace, isupper, isxdigit, tolower, toupper 

Example: 
#include <stdio.h> 
#include <ctype.h> 
char chars[] = { 
  'A', 
  'a', 
  'z', 
  'Z' 
}; 
#define SIZE sizeof( chars ) / sizeof( char ) 
void main() 
 { 
  int  i; 
  for( i = 0; i < SIZE; i++ ) { 
   printf( "Char %c is %sa lowercase character\n", 
      chars[i], 
      ( islower( chars[i] ) ) ? "" : "not " ); 
  } 
 } 
produces the following: 
Char A is not a lowercase character 
Char a is a lowercase character 
Char z is a lowercase character 
Char Z is not a lowercase character 

Classification: ANSI 

Systems: All


### isprint

Synopsis: 
#include <ctype.h> 
int isprint( int c ); 

Description: The isprint function tests for any printable character including space (' ').  The  isgraph function is similar, except that the space character is excluded from the character set being tested. 

Returns: The isprint function returns a non-zero value when the argument is a printable character; otherwise, zero is returned. 

See Also: isalnum, isalpha, iscntrl, isdigit, isgraph, islower, ispunct, isspace, isupper, isxdigit, tolower, toupper 

Example: 
#include <stdio.h> 
#include <ctype.h> 
char chars[] = { 
  'A', 
  0x09, 
  ' ', 
  0x7d 
}; 
#define SIZE sizeof( chars ) / sizeof( char ) 
void main() 
 { 
  int  i; 
  for( i = 0; i < SIZE; i++ ) { 
   printf( "Char %c is %sa printable character\n", 
      chars[i], 
      ( isprint( chars[i] ) ) ? "" : "not " ); 
  } 
 } 
produces the following: 
Char A is a printable character 
Char   is not a printable character 
Char  is a printable character 
Char } is a printable character 

Classification: ANSI 

Systems: All


### ispunct

Synopsis: 
#include <ctype.h> 
int ispunct( int c ); 

Description: The ispunct function tests for any punctuation character such as a comma (,) or a period (.). 

Returns: The ispunct function returns a non-zero value when the argument is a punctuation character; otherwise, zero is returned. 

See Also: isalnum, isalpha, iscntrl, isdigit, isgraph, islower, isprint, isspace, isupper, isxdigit, tolower, toupper 

Example: 
#include <stdio.h> 
#include <ctype.h> 
char chars[] = { 
  'A', 
  '!', 
  '.', 
  ',', 
  ':', 
  ';' 
}; 
#define SIZE sizeof( chars ) / sizeof( char ) 
void main() 
 { 
  int  i; 
  for( i = 0; i < SIZE; i++ ) { 
   printf( "Char %c is %sa punctuation character\n", 
      chars[i], 
      ( ispunct( chars[i] ) ) ? "" : "not " ); 
  } 
 } 
produces the following: 
Char A is not a punctuation character 
Char ! is a punctuation character 
Char . is a punctuation character 
Char , is a punctuation character 
Char : is a punctuation character 
Char ; is a punctuation character 

Classification: ANSI 

Systems: All


### isspace

Synopsis: 
#include <ctype.h> 
int isspace( int c ); 

Description: The isspace function tests for the following white-space characters: 

' ' space 

'\f' form feed 

'\n' new-line or linefeed 

'\r' carriage return 

'\t' horizontal tab 

'\v' vertical tab 

Returns: The isspace function returns a non-zero character when the argument is one of the indicated white-space characters; otherwise, zero is returned. 

See Also: isalnum, isalpha, iscntrl, isdigit, isgraph, islower, isprint, ispunct, isupper, isxdigit, tolower, toupper 

Example: 
#include <stdio.h> 
#include <ctype.h> 
char chars[] = { 
  'A', 
  0x09, 
  ' ', 
  0x7d 
}; 
#define SIZE sizeof( chars ) / sizeof( char ) 
void main() 
 { 
  int  i; 
  for( i = 0; i < SIZE; i++ ) { 
   printf( "Char %c is %sa space character\n", 
      chars[i], 
      ( isspace( chars[i] ) ) ? "" : "not " ); 
  } 
 } 
produces the following: 
Char A is not a space character 
Char   is a space character 
Char  is a space character 
Char } is not a space character 

Classification: ANSI 

Systems: All


### isupper

Synopsis: 
#include <ctype.h> 
int isupper( int c ); 

Description: The isupper function tests for any uppercase letter 'A' through 'Z'. 

Returns: The isupper returns a non-zero value when the argument is an uppercase letter; otherwise, zero is returned. 

See Also: isalnum, isalpha, iscntrl, isdigit, isgraph, islower, isprint, ispunct, isspace, isxdigit, tolower, toupper 

Example: 
#include <stdio.h> 
#include <ctype.h> 
char chars[] = { 
  'A', 
  'a', 
  'z', 
  'Z' 
}; 
#define SIZE sizeof( chars ) / sizeof( char ) 
void main() 
 { 
  int  i; 
  for( i = 0; i < SIZE; i++ ) { 
   printf( "Char %c is %san uppercase character\n", 
      chars[i], 
      ( isupper( chars[i] ) ) ? "" : "not " ); 
  } 
 } 
produces the following: 
Char A is an uppercase character 
Char a is not an uppercase character 
Char z is not an uppercase character 
Char Z is an uppercase character 

Classification: ANSI 

Systems: All


### isxdigit

Synopsis: 
#include <ctype.h> 
int isxdigit( int c ); 

Description: The isxdigit function tests for any hexadecimal-digit character.  These characters are the digits ('0' through '9') and the letters ('a' through 'f') and ('A' through 'F'). 

Returns: The isxdigit function returns a non-zero value when the argument is a hexadecimal digit; otherwise, zero is returned. 

See Also: isalnum, isalpha, iscntrl, isdigit, isgraph, islower, isprint, ispunct, isspace, isupper, tolower, toupper 

Example: 
#include <stdio.h> 
#include <ctype.h> 
char chars[] = { 
  'A', 
  '5', 
  '$' 
}; 
#define SIZE sizeof( chars ) / sizeof( char ) 
void main() 
 { 
  int  i; 
  for( i = 0; i < SIZE; i++ ) { 
   printf( "Char %c is %sa hexadecimal digit" 
      " character\n", chars[i], 
      ( isxdigit( chars[i] ) ) ? "" : "not " ); 
  } 
 } 
produces the following: 
Char A is a hexadecimal digit character 
Char 5 is a hexadecimal digit character 
Char $ is not a hexadecimal digit character 

Classification: ANSI 

Systems: All


### itoa

Synopsis: 
#include <stdlib.h> 
char *itoa( int value, char *buffer, int radix ); 

Description: The itoa function converts the binary integer value into the equivalent string in base radix notation storing the result in the character array pointed to by buffer.  A null character is appended to the result.  The size of buffer must be at least (8 * sizeof(int) + 1) bytes when converting values in base 2.  That makes the size 17 bytes on 16-bit machines, and 33 bytes on 32-bit machines.  If the value of radix is 10 and value is negative, then a minus sign is prepended to the result. 

Returns: The  itoa function returns the pointer to the result. 

See Also: atoi, strtol, utoa 

Example: 
#include <stdio.h> 
#include <stdlib.h> 
void main() 
 { 
  char buffer[20]; 
  int base; 
  for( base = 2; base <= 16; base = base + 2 ) 
   printf( "%2d %s\n", base, 
       itoa( 12765, buffer, base ) ); 
 } 
produces the following: 
 2 11000111011101 
 4 3013131 
 6 135033 
 8 30735 
10 12765 
12 7479 
14 491b 
16 31dd 

Classification: WATCOM 

Systems: All


### kbhit

Synopsis: 
#include <conio.h> 
int kbhit( void ); 

Description: The kbhit function tests whether or not a keystroke is currently available.  When one is available, the function  getch or  getche may be used to obtain the keystroke in question. 
With a stand-alone program, the kbhit function may be called continuously until a keystroke is available. 

Returns: The kbhit function returns zero when no keystroke is available; otherwise, a non-zero value is returned. 

See Also: getch, getche, putch, ungetch 

Example: 
/* 
 * This program loops until a key is pressed 
 * or a count is exceeded. 
 */ 
#include <stdio.h> 
#include <conio.h> 
void main() 
 { 
  unsigned long i; 
  printf( "Program looping. Press any key.\n" ); 
  for( i = 0; i < 10000; i++ ) { 
   if( kbhit() ) { 
    getch(); 
    break; 
   } 
  } 
 } 

Classification: WATCOM 

Systems: All


### labs

Synopsis: 
#include <stdlib.h> 
long int labs( long int j ); 

Description: The labs function returns the absolute value of its long-integer argument j. 

Returns: The labs function returns the absolute value of its argument. 

See Also: abs, fabs 

Example: 
#include <stdio.h> 
#include <stdlib.h> 
void main() 
 { 
  long x, y; 
  x = -50000L; 
  y = labs( x ); 
  printf( "labs(%ld) = %ld\n", x, y ); 
 } 
produces the following: 
labs(-50000) = 50000 

Classification: ANSI 

Systems: All


### ldexp

Synopsis: 
#include <math.h> 
double ldexp( double x, int exp ); 

Description: The ldexp function multiplies a floating-point number by an integral power of 2.  A range error may occur. 

Returns: The ldexp function returns the value of x times 2 raised to the power exp. 

See Also: frexp, modf 

Example: 
#include <stdio.h> 
#include <math.h> 
void main() 
 { 
  double value; 
  value = ldexp( 4.7072345, 5 ); 
  printf( "%f\n", value ); 
 } 
produces the following: 
150.631504 

Classification: ANSI 

Systems: All


### ldiv

Synopsis: 
#include <stdlib.h> 
ldiv_t ldiv( long int numer, long int denom ); 
typedef struct { 
  long int quot;   /* quotient */ 
  long int rem;    /* remainder */ 
} ldiv_t; 

Description: The ldiv function calculates the quotient and remainder of the division of the numerator numer by the denominator denom. 

Returns: The ldiv function returns a structure of type  ldiv_t that contains the fields  quot and  rem, which are both of type long int. 

See Also: div 

Example: 
#include <stdio.h> 
#include <stdlib.h> 
void print_time( long int ticks ) 
 { 
  ldiv_t sec_ticks; 
  ldiv_t min_sec; 
  sec_ticks = ldiv( ticks, 100L ); 
  min_sec  = ldiv( sec_ticks.quot, 60L ); 
  printf( "It took %ld minutes and %ld seconds\n", 
       min_sec.quot, min_sec.rem ); 
 } 
void main() 
 { 
  print_time( 86712L ); 
 } 
produces the following: 
It took 14 minutes and 27 seconds 

Classification: ANSI 

Systems: All


### lfind

Synopsis: 
#include <search.h> 
void *lfind( const void *key, /* object to search for  */ 
       const void *base,/* base of search data  */ 
       unsigned *num,  /* number of elements   */ 
       unsigned width,  /* width of each element */ 
       int (*compare)( const void *element1, 
               const void *element2 ) ); 

Description: The lfind function performs a linear search for the value key in the array of num elements pointed to by base.  Each element of the array is width bytes in size.  The argument compare is a pointer to a user-supplied routine that will be called by lfind to determine the relationship of an array element with the key.  One of the arguments to the compare function will be an array element, and the other will be key. 
The compare function should return 0 if element1 is identical to element2 and non-zero if the elements are not identical. 

Returns: The lfind function returns a pointer to the array element in base that matches key if it is found, otherwise NULL is returned indicating that the key was not found. 

See Also: bsearch, lsearch 

Example: 
#include <stdio.h> 
#include <stdlib.h> 
#include <string.h> 
#include <search.h> 
static const char *keywords[] = { 
    "auto", 
    "break", 
    "case", 
    "char", 
    /* . */ 
    /* . */ 
    /* . */ 
    "while" 
}; 
void main( int argc, const char *argv[] ) 
 { 
  unsigned num = 5; 
  int compare( const void *, const void * ); 
  if( argc <= 1 ) exit( EXIT_FAILURE ); 
  if( lfind( &argv[1], keywords, &num, sizeof(char **), 
          compare ) == NULL ) { 
   printf( "'%s' is not a C keyword\n", argv[1] ); 
   exit( EXIT_FAILURE ); 
  } else { 
   printf( "'%s' is a C keyword\n", argv[1] ); 
   exit( EXIT_SUCCESS ); 
  } 
 } 
int compare( const void *op1, const void *op2 ) 
 { 
  const char **p1 = (const char **) op1; 
  const char **p2 = (const char **) op2; 
  return( strcmp( *p1, *p2 ) ); 
 } 

Classification: WATCOM 

Systems: All


### _lineto, _lineto_w

Synopsis: 
#include <graph.h> 
short _FAR _lineto( short x, short y ); 
short _FAR _lineto_w( double x, double y ); 

Description: The _lineto functions draw straight lines.  The _lineto function uses the view coordinate system.  The _lineto_w function uses the window coordinate system. 
The line is drawn from the current position to the point at the coordinates (x,y).  The point (x,y) becomes the new current position.  The line is drawn with the current plotting action using the current line style and the current color. 

Returns: The _lineto functions return a non-zero value when the line was successfully drawn; otherwise, zero is returned. 

See Also: _moveto, _setcolor, _setlinestyle, _setplotaction 

Example: 
#include <conio.h> 
#include <graph.h> 
main() 
{ 
  _setvideomode( _VRES16COLOR ); 
  _moveto( 100, 100 ); 
  _lineto( 540, 100 ); 
  _lineto( 320, 380 ); 
  _lineto( 100, 100 ); 
  getch(); 
  _setvideomode( _DEFAULTMODE ); 
} 
produces the following: 
The graphical image cannot be reproduced here. See the printed 
version of the manual. 

Classification: PC Graphics 

Systems:  _lineto - DOS, QNX 
_lineto_w - DOS, QNX


### localeconv

Synopsis: 
#include <locale.h> 
struct lconv *localeconv( void ); 

Description: The localeconv function sets the components of an object of type  struct lconv with values appropriate for the formatting of numeric quantities according to the current locale.  The components of the  struct lconv and their meanings are as follows: 

char *decimal_point The decimal-point character used to format non-monetary quantities. 

char *thousands_sep The character used to separate groups of digits to the left of the decimal-point character in formatted non-monetary quantities. 

char *grouping A string whose elements indicate the size of each group of digits in formatted non-monetary quantities. 

char *int_curr_symbol The international currency symbol applicable to the current locale.  The first three characters contain the alphabetic international currency symbol in accordance with those specified in ISO 4217 Codes for the Representation of Currency and Funds.  The fourth character (immediately preceding the null character) is the character used to separate the international currency symbol from the monetary quantity. 

char *currency_symbol The local currency symbol applicable to the current locale. 

char *mon_decimal_point The decimal-point character used to format monetary quantities. 

char *mon_thousands_sep The character used to separate groups of digits to the left of the decimal-point character in formatted monetary quantities. 

char *mon_grouping A string whose elements indicate the size of each group of digits in formatted monetary quantities. 

char *positive_sign The string used to indicate a nonnegative-valued monetary quantity. 

char *negative_sign The string used to indicate a negative-valued monetary quantity. 

char int_frac_digits The number of fractional digits (those to the right of the decimal-point) to be displayed in an internationally formatted monetary quantity. 

char frac_digits The number of fractional digits (those to the right of the decimal-point) to be displayed in a formatted monetary quantity. 

char p_cs_precedes Set to 1 or 0 if the  currency_symbol respectively precedes or follows the value for a nonnegative formatted monetary quantity. 

char p_sep_by_space Set to 1 or 0 if the  currency_symbol respectively is or is not separated by a space from the value for a nonnegative formatted monetary quantity. 

char n_cs_precedes Set to 1 or 0 if the  currency_symbol respectively precedes or follows the value for a negative formatted monetary quantity. 

char n_sep_by_space Set to 1 or 0 if the  currency_symbol respectively is or is not separated by a space from the value for a negative formatted monetary quantity. 

char p_sign_posn The position of the  positive_sign for a nonnegative formatted monetary quantity. 

char n_sign_posn The position of the  positive_sign for a negative formatted monetary quantity. 
The elements of  grouping and  mon_grouping are interpreted according to the following: 

CHAR_MAX No further grouping is to be performed. 

0 The previous element is to be repeatedly used for the remainder of the digits. 

other The value is the number of digits that comprise the current group.  The next element is examined to determine the size of the next group of digits to the left of the current group. 
The value of  p_sign_posn and  n_sign_posn is interpreted as follows: 

0 Parentheses surround the quantity and  currency_symbol. 

1 The sign string precedes the quantity and  currency_symbol. 

2 The sign string follows the quantity and  currency_symbol. 

3 The sign string immediately precedes the quantity and  currency_symbol. 

4 The sign string immediately follows the quantity and  currency_symbol. 

Returns: The localeconv function returns a pointer to the filled-in object. 

See Also: setlocale 

Example: 
#include <stdio.h> 
#include <locale.h> 
void main() 
 { 
  struct lconv *lc; 
  lc = localeconv(); 
  printf( "*decimal_point (%s)\n", 
    lc->decimal_point ); 
  printf( "*thousands_sep (%s)\n", 
    lc->thousands_sep ); 
  printf( "*int_curr_symbol (%s)\n", 
    lc->int_curr_symbol ); 
  printf( "*currency_symbol (%s)\n", 
    lc->currency_symbol ); 
  printf( "*mon_decimal_point (%s)\n", 
    lc->mon_decimal_point ); 
  printf( "*mon_thousands_sep (%s)\n", 
    lc->mon_thousands_sep ); 
  printf( "*mon_grouping (%s)\n", 
    lc->mon_grouping ); 
  printf( "*grouping (%s)\n", 
    lc->grouping ); 
  printf( "*positive_sign (%s)\n", 
    lc->positive_sign ); 
  printf( "*negative_sign (%s)\n", 
    lc->negative_sign ); 
  printf( "int_frac_digits (%d)\n", 
    lc->int_frac_digits ); 
  printf( "frac_digits (%d)\n", 
    lc->frac_digits ); 
  printf( "p_cs_precedes (%d)\n", 
    lc->p_cs_precedes ); 
  printf( "p_sep_by_space (%d)\n", 
    lc->p_sep_by_space ); 
  printf( "n_cs_precedes (%d)\n", 
    lc->n_cs_precedes ); 
  printf( "n_sep_by_space (%d)\n", 
    lc->n_sep_by_space ); 
  printf( "p_sign_posn (%d)\n", 
    lc->p_sign_posn ); 
  printf( "n_sign_posn (%d)\n", 
    lc->n_sign_posn ); 
 } 

Classification: ANSI 

Systems: All


### localtime Functions

Synopsis: 
#include <time.h> 
struct tm * localtime( const time_t *timer ); 
struct tm *_localtime( const time_t *timer, 
            struct tm *tmbuf ); 
struct  tm { 
 int tm_sec;  /* seconds after the minute -- [0,61] */ 
 int tm_min;  /* minutes after the hour  -- [0,59] */ 
 int tm_hour;  /* hours after midnight   -- [0,23] */ 
 int tm_mday;  /* day of the month     -- [1,31] */ 
 int tm_mon;  /* months since January   -- [0,11] */ 
 int tm_year;  /* years since 1900          */ 
 int tm_wday;  /* days since Sunday     -- [0,6]  */ 
 int tm_yday;  /* days since January 1   -- [0,365]*/ 
 int tm_isdst; /* Daylight Savings Time flag */ 
}; 

Description: The localtime functions convert the calendar time pointed to by timer into a structure of type  tm, of time information, expressed as local time.  Whenever localtime is called, the  tzset function is also called. 
The calendar time is usually obtained by using the  time function.  That time is Coordinated Universal Time (UTC) (formerly known as Greenwich Mean Time (GMT)). 
The function  _localtime places the converted time in the  tm structure pointed to by tmbuf, and the function  localtime places the converted time in a static structure that is re-used each time  localtime is called. 
The time set on the computer with the DOS time command and the DOS date command reflects the local time.  The environment variable TZ is used to establish the time zone to which this local time applies.  See the section The TZ Environment Variable for a discussion of how to set the time zone. 

Returns: The localtime functions return a pointer to a  tm structure containing the time information. 

See Also: asctime, clock, ctime, difftime, gmtime, mktime, strftime, time, tzset 

Example: 
#include <stdio.h> 
#include <time.h> 
void main() 
 { 
  time_t time_of_day; 
  auto char buf[26]; 
  auto struct tm tmbuf; 
  time_of_day = time( NULL ); 
  _localtime( &time_of_day, &tmbuf ); 
  printf( "It is now: %s", _asctime( &tmbuf, buf ) ); 
 } 
produces the following: 
It is now: Sat Mar 21 15:58:27 1987 

Classification: localtime is ANSI, _localtime is not ANSI 

Systems:  localtime - All 
_localtime - All


### lock

Synopsis: 
#include <io.h> 
int lock( int handle, 
     unsigned long offset, 
     unsigned long nbytes ); 

Description: The lock function locks nbytes amount of data in the file designated by handle starting at byte offset in the file.  This prevents other processes from reading or writing into the locked region until an  unlock has been done for this locked region of the file. 
Multiple regions of a file can be locked, but no overlapping regions are allowed.  You cannot unlock multiple regions in the same call, even if the regions are contiguous.  All locked regions of a file should be unlocked before closing a file or exiting the program. 
With DOS, locking is supported by version 3.0 or later.  Note that SHARE.COM or SHARE.EXE must be installed. 

Returns: The lock function returns zero if successful, and -1 when an error occurs.  When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

See Also: locking, open, sopen, unlock 

Example: 
#include <stdio.h> 
#include <fcntl.h> 
#include <io.h> 
void main() 
 { 
  int handle; 
  char buffer[20]; 
  handle = open( "file", O_RDWR | O_TEXT ); 
  if( handle != -1 ) { 
   if( lock( handle, 0L, 20L ) ) { 
    printf( "Lock failed\n" ); 
   } else { 
    read( handle, buffer, 20 ); 
    /* update the buffer here */ 
    lseek( handle, 0L, SEEK_SET ); 
    write( handle, buffer, 20 ); 
    unlock( handle, 0L, 20L ); 
   } 
   close( handle ); 
  } 
 } 

Classification: WATCOM 

Systems: All


### locking

Synopsis: 
#include <sys\locking.h> 
int locking( int handle, int mode, long nbyte ); 

Description: The locking function locks or unlocks nbyte bytes of the file specified by handle.  Locking a region of a file prevents other processes from reading or writing the locked region until the region has been unlocked.  The locking and unlocking takes place at the current file position.  The argument mode specifies the action to be performed.  The possible values for mode are: 

LK_LOCK Locks the specified region.  The function will retry to lock the region after 1 second intervals until successful or until 10 attempts have been made. 

LK_RLCK Same action as  LK_LOCK. 

LK_NBLCK Non-blocking lock:  makes only 1 attempt to lock the specified region. 

LK_NBRLCK Same action as  LK_NBLCK. 

LK_UNLCK Unlocks the specified region.  The region must have been previously locked. 
Multiple regions of a file can be locked, but no overlapping regions are allowed.  You cannot unlock multiple regions in the same call, even if the regions are contiguous.  All locked regions of a file should be unlocked before closing a file or exiting the program. 
With DOS, locking is supported by version 3.0 or later.  Note that SHARE.COM or SHARE.EXE must be installed. 

Returns: The locking function returns zero if successful.  Otherwise, it returns -1 and  errno is set to indicate the error. 

Errors: When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

EACCES Indicates a locking violation (file already locked or unlocked). 

EBADF Indicates an invalid file handle. 

EDEADLOCK Indicates a locking violation.  This error is returned when mode is LK_LOCK or LK_RLCK and the file cannot be locked after 10 attempts. 

EINVAL Indicates that an invalid argument was given to the function. 

See Also: creat, _dos_creat, _dos_open, lock, open, sopen, unlock 

Example: 
#include <stdio.h> 
#include <sys\locking.h> 
#include <share.h> 
#include <fcntl.h> 
#include <io.h> 
void main() 
 { 
  int handle; 
  unsigned nbytes; 
  unsigned long offset; 
  auto char buffer[512]; 
  nbytes = 512; 
  offset = 1024; 
  handle = sopen( "db.fil", O_RDWR, SH_DENYNO ); 
  if( handle != -1 ) { 
   lseek( handle, offset, SEEK_SET ); 
   locking( handle, LK_LOCK, nbytes ); 
   read( handle, buffer, nbytes ); 
   /* update data in the buffer */ 
   lseek( handle, offset, SEEK_SET ); 
   write( handle, buffer, nbytes ); 
   lseek( handle, offset, SEEK_SET ); 
   locking( handle, LK_UNLCK, nbytes ); 
   close( handle ); 
  } 
 } 

Classification: WATCOM 

Systems: All


### log

Synopsis: 
#include <math.h> 
double log( double x ); 

Description: The log function computes the natural logarithm (base e) of x.  A domain error occurs if the argument is negative.  A range error occurs if the argument is zero. 

Returns: The log function returns the natural logarithm of the argument.  When the argument is outside the permissible range, the  matherr function is called.  Unless the default  matherr function is replaced, it will set the global variable  errno to  EDOM, and print a "DOMAIN error" diagnostic message using the  stderr stream. 

See Also: exp, log10, log2, pow, matherr 

Example: 
#include <stdio.h> 
#include <math.h> 
void main() 
 { 
  printf( "%f\n", log(.5) ); 
 } 
produces the following: 
-0.693147 

Classification: ANSI 

Systems: All


### log10

Synopsis: 
#include <math.h> 
double log10( double x ); 

Description: The log10 function computes the logarithm (base 10) of x.  A domain error occurs if the argument is negative.  A range error occurs if the argument is zero. 

Returns: The log10 function returns the logarithm (base 10) of the argument.  When the argument is outside the permissible range, the  matherr function is called.  Unless the default  matherr function is replaced, it will set the global variable  errno to  EDOM, and print a "DOMAIN error" diagnostic message using the  stderr stream. 

See Also: exp, log, log2, pow, matherr 

Example: 
#include <stdio.h> 
#include <math.h> 
void main() 
 { 
  printf( "%f\n", log10(.5) ); 
 } 
produces the following: 
-0.301030 

Classification: ANSI 

Systems: All


### log2

Synopsis: 
#include <math.h> 
double log2( double x ); 

Description: The log2 function computes the logarithm (base 2) of x.  A domain error occurs if the argument is negative.  A range error occurs if the argument is zero. 

Returns: The log2 function returns the logarithm (base 2) of the argument.  When the argument is outside the permissible range, the  matherr function is called.  Unless the default  matherr function is replaced, it will set the global variable  errno to  EDOM, and print a "DOMAIN error" diagnostic message using the  stderr stream. 

See Also: exp, log, log10, pow, matherr 

Example: 
#include <stdio.h> 
#include <math.h> 
void main() 
 { 
  printf( "%f\n", log2(.25) ); 
 } 
produces the following: 
-2.000000 

Classification: WATCOM 

Systems: All


### longjmp

Synopsis: 
#include <setjmp.h> 
void longjmp( jmp_buf env, int return_value ); 

Description: The longjmp function restores the environment saved by the most recent call to the  setjmp function with the corresponding  jmp_buf argument. 

Returns: After the longjmp function restores the environment, program execution continues as if the corresponding call to  setjmp had just returned the value specified by return_value.  If the value of return_value is 0, the value returned is 1. 

See Also: setjmp 

Example: 
#include <stdio.h> 
#include <setjmp.h> 
jmp_buf env; 
rtn() 
 { 
  printf( "about to longjmp\n" ); 
  longjmp( env, 14 ); 
 } 
void main() 
 { 
  int ret_val = 293; 
  if( 0 == ( ret_val = setjmp( env ) ) ) { 
   printf( "after setjmp %d\n", ret_val ); 
   rtn(); 
   printf( "back from rtn %d\n", ret_val ); 
  } else { 
   printf( "back from longjmp %d\n", ret_val ); 
  } 
 } 
produces the following: 
after setjmp 0 
about to longjmp 
back from longjmp 14 

Classification: ANSI 

Systems: All


### _lrotl

Synopsis: 
#include <stdlib.h> 
unsigned long _lrotl( unsigned long value, 
           unsigned int shift ); 

Description: The _lrotl function rotates the unsigned long integer, determined by value, to the left by the number of bits specified in shift. 

Returns: The rotated value is returned. 

See Also: _lrotr, _rotl, _rotr 

Example: 
#include <stdio.h> 
#include <stdlib.h> 
unsigned long mask = 0x12345678; 
void main() 
 { 
  mask = _lrotl( mask, 4 ); 
  printf( "%08lX\n", mask ); 
 } 
produces the following: 
23456781 

Classification: WATCOM 

Systems: All


### _lrotr

Synopsis: 
#include <stdlib.h> 
unsigned long _lrotr( unsigned long value, 
           unsigned int shift ); 

Description: The _lrotr function rotates the unsigned long integer, determined by value, to the right by the number of bits specified in shift. 

Returns: The rotated value is returned. 

See Also: _lrotl, _rotl, _rotr 

Example: 
#include <stdio.h> 
#include <stdlib.h> 
unsigned long mask = 0x12345678; 
void main() 
 { 
  mask = _lrotr( mask, 4 ); 
  printf( "%08lX\n", mask ); 
 } 
produces the following: 
81234567 

Classification: WATCOM 

Systems: All


### lsearch

Synopsis: 
#include <search.h> 
void *lsearch( const void *key, /* object to search for */ 
        const void *base,/* base of search data  */ 
        unsigned *num,  /* number of elements  */ 
        unsigned width,  /* width of each element*/ 
        int (*compare)( const void *element1, 
                const void *element2 ) ); 

Description: The lsearch function performs a linear search for the value key in the array of num elements pointed to by base.  Each element of the array is width bytes in size.  The argument compare is a pointer to a user-supplied routine that will be called by lsearch to determine the relationship of an array element with the key.  One of the arguments to the compare function will be an array element, and the other will be key. 
The compare function should return 0 if element1 is identical to element2 and non-zero if the elements are not identical. 

Returns: If the key value is not found in the array, then it is added to the end of the array and the number of elements is incremented.  The lsearch function returns a pointer to the array element in base that matches key if it is found, or the newly added key if it was not found. 

See Also: bsearch, lfind 

Example: 
#include <stdio.h> 
#include <stdlib.h> 
#include <string.h> 
#include <search.h> 
void main( int argc, const char *argv[] ) 
 { 
  int i; 
  unsigned num = 0; 
  char **array = (char **)calloc( argc, sizeof(char **) ); 
  int compare( const void *, const void * ); 
  for( i = 1; i < argc; ++i ) { 
   lsearch( &argv[i], array, &num, sizeof(char **), 
         compare ); 
  } 
  for( i = 0; i < num; ++i ) { 
   printf( "%s\n", array[i] ); 
  } 
 } 
int compare( const void *op1, const void *op2 ) 
 { 
  const char **p1 = (const char **) op1; 
  const char **p2 = (const char **) op2; 
  return( strcmp( *p1, *p2 ) ); 
 } 
/* With input: one two one three four */ 
produces the following: 
one 
two 
three 
four 

Classification: WATCOM 

Systems: All


### lseek

Synopsis: 
#include <stdio.h> 
#include <io.h> 
long int lseek( int handle, long int offset, int whence ); 

Description: The lseek function sets the current file position at the operating system level.  The file is referenced using the file handle handle returned by a successful execution of one of the  creat,  dup,  dup2,  open or  sopen functions.  The value of offset is used as a relative offset from a file position determined by the value of the argument whence. 
The new file position is determined in a manner dependent upon the value of whence which may have one of three possible values (defined in the <stdio.h> header file): 

SEEK_SET The new file position is computed relative to the start of the file.  The value of offset must not be negative. 

SEEK_CUR The new file position is computed relative to the current file position.  The value of offset may be positive, negative or zero. 

SEEK_END The new file position is computed relative to the end of the file. 
An error will occur if the requested file position is before the start of the file. 
The requested file position may be beyond the end of the file.  If data is later written at this point, subsequent reads of data in the gap will return bytes whose value is equal to zero until data is actually written in the gap. 
Some versions of MS-DOS allow seeking to a negative offset, but it is not recommended since it is not supported by other platforms and may not be supported in future versions of MS-DOS. 
The lseek function does not, in itself, extend the size of a file (see the description of the  chsize function). 

Returns: If successful, the current file position is returned in a system-dependent manner.  A value of 0 indicates the start of the file.  When an error occurs, -1 is returned and  errno is set to indicate the error. 

Errors: When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

EBADF The handle argument is not a valid file handle. 

EINVAL The whence argument is not a proper value, or the resulting file offset would be invalid. 

See Also: chsize, close, creat, dup, dup2, eof, exec Functions, filelength, fileno, fstat, isatty, open, read, setmode, sopen, stat, tell, write, umask 

Example: 
The lseek function can be used to obtain the current file position (the  tell function is implemented in terms of lseek).  This value can then be used with the lseek function to reset the file position to that point in the file: 
long int file_posn; 
int handle; 
/* get current file position */ 
file_posn = lseek( handle, 0L, SEEK_CUR ); 
 /* or */ 
file_posn = tell( handle ); 
/* return to previous file position */ 
file_posn = lseek( handle, file_posn, SEEK_SET ); 
If all records in the file are the same size, the position of the n'th record can be calculated and read, as illustrated in the following sample function: 
#include <stdio.h> 
#include <io.h> 
int read_record( int  handle, 
         long rec_numb, 
         int  rec_size, 
         char *buffer ) 
 { 
  if( lseek( handle, rec_numb * rec_size, SEEK_SET ) 
     == -1L ) { 
   return( -1 ); 
  } 
  return( read( handle, buffer, rec_size ) ); 
 } 
The function in this example assumes records are numbered starting with zero and that rec_size contains the size of a record in the file (including the carriage-return character in text files). 

Classification: POSIX 1003.1 

Systems: All


### ltoa

Synopsis: 
#include <stdlib.h> 
char *ltoa( long int value, 
      char *buffer, 
      int radix ); 

Description: The ltoa function converts the binary integer value into the equivalent string in base radix notation storing the result in the character array pointed to by buffer.  A null character is appended to the result.  The size of buffer must be at least 33 bytes when converting values in base 2.  If the value of radix is 10 and value is negative, then a minus sign is prepended to the result. 

Returns: The ltoa function returns a pointer to the result. 

See Also: atol, strtol, strtoul, ultoa 

Example: 
#include <stdio.h> 
#include <stdlib.h> 
void print_value( long value ) 
 { 
  int base; 
  char buffer[33]; 
  for( base = 2; base <= 16; base = base + 2 ) 
   printf( "%2d %s\n", base, 
       ltoa( value, buffer, base ) ); 
 } 
void main() 
 { 
  print_value( 12765L ); 
 } 
produces the following: 
 2 11000111011101 
 4 3013131 
 6 135033 
 8 30735 
10 12765 
12 7479 
14 491b 
16 31dd 

Classification: WATCOM 

Systems: All


### main

Synopsis: 
int main( void ); 
int main( int argc, const char *argv[] ); 

Description: The function main is a user-supplied function where program execution begins.  The command line to the program is broken into a sequence of tokens separated by blanks and are passed to main as an array of pointers to character strings in the parameter argv.  The number of arguments found is passed in the parameter argc.  The first element of argv will be a pointer to a character string containing the program name.  The last element of the array pointed to by argv will be a NULL pointer (i.e.  argv[argc] will be NULL).  Arguments that contain blanks can be passed to  main by enclosing them within double quote characters (which are removed from that element in the argv vector. 
The command line arguments can also be obtained in its original format by using the  getcmd function. 

Returns: The function  main returns a return code back to the calling program (usually the operating system). 

See Also: abort, atexit, _bgetcmd, exec Functions, exit, _exit, getcmd, getenv, onexit, putenv, spawn Functions, system 

Example: 
#include <stdio.h> 
int main( int argc, char *argv[] ) 
 { 
  int i; 
  for( i = 0; i < argc; ++i ) { 
   printf( "argv[%d] = %s\n", i, argv[i] ); 
  } 
  return( 0 ); 
 } 
produces the following: 
argv[0] = C:\WATCOM\DEMO\MYPGM.EXE 
argv[1] = hhhhh 
argv[2] = another arg 
when the program mypgm is executed with the command 
mypgm hhhhh  "another arg" 

Classification: ANSI 

Systems: All


### _makepath

Synopsis: 
#include <stdlib.h> 
void _makepath( char *path, 
        const char *drive, 
        const char *dir, 
        const char *fname, 
        const char *ext ); 

Description: The _makepath function constructs a full pathname from the components consisting of a drive letter, directory path, file name and file name extension.  The full pathname is placed in the buffer pointed to by the argument path. 
The maximum size required for each buffer is specified by the manifest constants  _MAX_PATH,  _MAX_DRIVE,  _MAX_DIR,  _MAX_FNAME, and  _MAX_EXT which are defined in <stdlib.h>. 

drive The drive argument points to a buffer containing the drive letter (A, B, C, etc.) followed by an optional colon.  The _makepath function will automatically insert a colon in the full pathname if it is missing.  If drive is a NULL pointer or points to an empty string, no drive letter or colon will be placed in the full pathname. 

dir The dir argument points to a buffer containing just the pathname.  Either forward slashes (/) or backslashes (\) may be used.  The trailing slash is optional.  The _makepath function will automatically insert a trailing slash in the full pathname if it is missing.  If dir is a NULL pointer or points to an empty string, no slash will be placed in the full pathname. 

fname The fname argument points to a buffer containing the base name of the file without any extension (suffix). 

ext The ext argument points to a buffer containing the filename extension or suffix.  A leading period (.) is optional.  The _makepath routine will automatically insert a period in the full pathname if it is missing.  If ext is a NULL pointer or points to an empty string, no period will be placed in the full pathname. 

Returns: The _makepath function returns no value. 

See Also: _fullpath, _splitpath 

Example: 
#include <stdio.h> 
#include <stdlib.h> 
void main() 
 { 
  char full_path[ _MAX_PATH ]; 
  char drive[ _MAX_DRIVE ]; 
  char dir[ _MAX_DIR ]; 
  char fname[ _MAX_FNAME ]; 
  char ext[ _MAX_EXT ]; 
  _makepath(full_path,"c","watcomc\\h\\","stdio","h"); 
  printf( "Full path is: %s\n\n", full_path ); 
  _splitpath( full_path, drive, dir, fname, ext ); 
  printf( "Components after _splitpath\n" ); 
  printf( "drive: %s\n", drive ); 
  printf( "dir:  %s\n", dir ); 
  printf( "fname: %s\n", fname ); 
  printf( "ext:  %s\n", ext ); 
 } 
produces the following: 
Full path is: c:watcomc\h\stdio.h 
Components after _splitpath 
drive: c: 
dir:  watcomc\h\ 
fname: stdio 
ext:  .h 
Note the use of two adjacent backslash characters (\) within character-string constants to signify a single backslash. 

Classification: WATCOM 

Systems: All


### malloc Functions

Synopsis: 
#include <stdlib.h>  For ANSI compatibility (malloc only) 
#include <malloc.h>  Required for other function prototypes 
void *malloc( size_t size ); 
void __based(void) *_bmalloc( __segment seg, size_t size ); 
void __far  *_fmalloc( size_t size ); 
void __near *_nmalloc( size_t size ); 

Description: The  malloc functions allocate space for an object of size bytes.  Nothing is allocated when the size argument has a value of zero. 
Each function allocates memory from a particular heap, as listed below: 

malloc Depends on data model of the program 

_bmalloc Based heap specified by seg value 

_fmalloc Far heap (outside the default data segment) 

_nmalloc Near heap (inside the default data segment) 
In a small data memory model, the  malloc function is equivalent to the  _nmalloc function; in a large data memory model, the  malloc function is equivalent to the  _fmalloc function. 

Returns: The  malloc functions return a pointer to the start of the allocated memory.  The  malloc,  _fmalloc and  _nmalloc functions return NULL if there is insufficient memory available or if the requested size is zero.  The  _bmalloc function returns  _NULLOFF if there is insufficient memory available or if the requested size is zero. 

See Also: calloc Functions, _expand Functions, free Functions, halloc, hfree, _msize Functions, realloc Functions, sbrk 

Example: 
#include <stdlib.h> 
void main() 
 { 
  char *buffer; 
  buffer = (char *)malloc( 80 ); 
  if( buffer != NULL ) { 
    /* body of program */ 
    free( buffer ); 
  } 
 } 

Classification: malloc is ANSI; _bmalloc, _fmalloc, _nmalloc are not ANSI 

Systems:  malloc - All 
_bmalloc - DOS/16, Win/16, QNX/16, OS/2 1.x(all) 
_fmalloc - DOS/16, Win/16, QNX/16, OS/2 1.x(all) 
_nmalloc - DOS, Win, QNX, OS/2 1.x, OS/2 1.x(MT), OS/2 2.x, NT


### matherr

Synopsis: 
#include <math.h> 
int matherr( struct exception *err_info ); 

Description: The matherr function is invoked each time an error is detected by functions in the math library.  The default matherr function supplied in the library returns zero which causes an error message to be displayed upon  stderr and  errno to be set with an appropriate error value.  An alternative version of this function can be provided, instead of the library version, in order that the error handling for mathematical errors can be handled by an application. 
A program may contain a user-written version of matherr to take any appropriate action when an error is detected.  When zero is returned, an error message will be printed upon  stderr and  errno will be set as was the case with the default function.  When a non-zero value is returned, no message is printed and  errno is not changed.  The value err_info->retval is used as the return value for the function in which the error was detected. 
The matherr function is passed a pointer to a structure of type struct exception which contains information about the error that has been detected: 
    
   struct exception 
   { int type;    /* TYPE OF ERROR         */ 
    char *name;   /* NAME OF FUNCTION       */ 
    double arg1;  /* FIRST ARGUMENT TO FUNCTION  */ 
    double arg2;  /* SECOND ARGUMENT TO FUNCTION  */ 
    double retval; /* DEFAULT RETURN VALUE     */ 
   }; 
The type field will contain one of the following values: 

DOMAIN A domain error has occurred, such as sqrt(-1e0). 

SING A singularity will result, such as pow(0e0,-2). 

OVERFLOW An overflow will result, such as pow(10e0,100). 

UNDERFLOW An underflow will result, such as pow(10e0,-100). 

TLOSS Total loss of significance will result, such as exp(1000). 

PLOSS Partial loss of significance will result, such as sin(10e70). 
The name field points to a string containing the name of the function which detected the error.  The fields arg1 and arg2 (if required) give the values which caused the error.  The field retval contains the value which will be returned by the function.  This value may be changed by a user-supplied version of the matherr function. 

Returns: The matherr function returns zero when an error message is to be printed and a non-zero value otherwise. 

Example: 
#include <stdio.h> 
#include <stdlib.h> 
#include <string.h> 
#include <math.h> 
/* Demonstrate error routine in which negative */ 
/* arguments to "sqrt" are treated as positive */ 
void main() 
 { 
  printf( "%e\n", sqrt( -5e0 ) ); 
  exit( 0 ); 
 } 
int matherr( struct exception *err ) 
 { 
  if( strcmp( err->name, "sqrt" ) == 0 ) { 
   if( err->type == DOMAIN ) { 
    err->retval = sqrt( -(err->arg1) ); 
    return( 1 ); 
   } else 
    return( 0 ); 
  } else 
   return( 0 ); 
 } 

Classification: WATCOM 

Systems: All


### max

Synopsis: 
#include <stdlib.h> 
#define max(a,b)  (((a) > (b)) ? (a) : (b)) 

Description: The max macro will evaluate to be the greater of two values.  It is implemented as follows. 
    
   #define max(a,b)  (((a) > (b)) ? (a) : (b)) 

Returns: The max macro will evaluate to the larger of the two values passed. 

See Also: min 

Example: 
#include <stdio.h> 
#include <stdlib.h> 
void main() 
 { 
  int a; 
  /* 
   * The following line will set the variable "a" to 10 
   * since 10 is greater than 1. 
   */ 
  a = max( 1, 10 ); 
  printf( "The value is: %d\n", a ); 
 } 

Classification: WATCOM 

Systems: All


### mblen

Synopsis: 
#include <stdlib.h> 
int mblen( const char *s, size_t n ); 

Description: The mblen function determines the number of bytes comprising the multibyte character pointed to by s.  At most n bytes of the array pointed to by s will be examined. 

Returns: If s is a NULL pointer, the mblen function returns zero if multibyte character encodings do not have state-dependent encoding, and non-zero otherwise.  If s is not a NULL pointer, the mblen function returns: 

0 if s points to the null character 

len the number of bytes that comprise the multibyte character (if the next n or fewer bytes form a valid multibyte character) 

-1 if the next n bytes do not form a valid multibyte character 

See Also: mbtowc, mbstowcs, wctomb, wcstombs 

Example: 
#include <stdio.h> 
#include <stdlib.h> 
void main() 
 { 
  int   len; 
  char   *mbs = "string"; 
  printf( "Character encodings do %shave " 
      "state-dependent encoding\n", 
      ( mblen( NULL, 0 ) ) 
      ? "" : "not " ); 
  len = mblen( "string", 6 ); 
  if( len != -1 ) { 
   mbs[len] = '\0'; 
   printf( "Multibyte char '%s'(%d)\n", mbs, len ); 
  } 
 } 
produces the following: 
Character encodings do not have state-dependent encoding 
Multibyte char 's'(1) 

Classification: ANSI 

Systems: All


### mbstowcs

Synopsis: 
#include <stdlib.h> 
size_t mbstowcs( wchar_t *pwcs, const char *s, size_t n ); 

Description: The mbstowcs function converts a sequence of multibyte characters pointed to by s into their corresponding wide character codes and stores not more than n codes into the array pointed to by pwcs.  The mbstowcs function does not convert any multibyte characters beyond the null character.  At most n elements of the array pointed to by pwcs will be modified. 

Returns: If an invalid multibyte character is encountered, the mbstowcs function returns (size_t)-1.  Otherwise, the mbstowcs function returns the number of array elements modified, not including the terminating zero code if present. 

See Also: mblen, mbtowc, wctomb, wcstombs 

Example: 
#include <stdio.h> 
#include <stdlib.h> 
void main() 
 { 
  char   *wc = "string"; 
  wchar_t wbuffer[50]; 
  int   i, len; 
  len = mbstowcs( wbuffer, wc, 50 ); 
  if( len != -1 ) { 
   wbuffer[len] = '\0'; 
   printf( "%s(%d)\n", wc, len ); 
   for( i = 0; i < len; i++ ) 
    printf( "/%4.4x", wbuffer[i] ); 
   printf( "\n" ); 
  } 
 } 
produces the following: 
string(6) 
/0073/0074/0072/0069/006e/0067 

Classification: ANSI 

Systems: All


### mbtowc

Synopsis: 
#include <stdlib.h> 
int mbtowc( wchar_t *pwc, const char *s, size_t n ); 

Description: The mbtowc function converts a single multibyte character pointed to by s into the wide character code that corresponds to that multibyte character.  The code for the null character is zero.  If the multibyte character is valid and pwc is not a NULL pointer, the code is stored in the object pointed to by pwc.  At most n bytes of the array pointed to by s will be examined. 

Returns: If s is a NULL pointer, the mbtowc function returns zero if multibyte character encodings do not have state-dependent encoding, and non-zero otherwise.  If s is not a NULL pointer, the mbtowc function returns: 

0 if s points to the null character 

len the number of bytes that comprise the multibyte character (if the next n or fewer bytes form a valid multibyte character) 

-1 if the next n bytes do not form a valid multibyte character 

See Also: mblen, wctomb, mbstowcs, wcstombs 

Example: 
#include <stdio.h> 
#include <stdlib.h> 
void main() 
 { 
  char   *wc = "string"; 
  wchar_t wbuffer[10]; 
  int   i, len; 
  printf( "Character encodings do %shave " 
      "state-dependent encoding\n", 
      ( mbtowc( wbuffer, NULL, 0 ) ) 
      ? "" : "not " ); 
  len = mbtowc( wbuffer, wc, 2 ); 
  wbuffer[len] = '\0'; 
  printf( "%s(%d)\n", wc, len ); 
  for( i = 0; i < len; i++ ) 
    printf( "/%4.4x", wbuffer[i] ); 
  printf( "\n" ); 
 } 
produces the following: 
Character encodings do not have state-dependent encoding 
string(1) 
/0073 

Classification: ANSI 

Systems: All


### _memavl

Synopsis: 
#include <malloc.h> 
size_t _memavl( void ); 

Description: The _memavl function returns the number of bytes of memory available for dynamic memory allocation in the near heap (the default data segment).  In the tiny, small and medium memory models, the default data segment is only extended as needed to satisfy requests for memory allocation.  Therefore, you will need to call  _nheapgrow in these memory models before calling _memavl in order to get a meaningful result. 
The number returned by _memavl may not represent a single contiguous block of memory.  Use the  _memmax function to find the largest contiguous block of memory that can be allocated. 

Returns: The _memavl function returns the number of bytes of memory available for dynamic memory allocation in the near heap (the default data segment). 

See Also: calloc Functions, _freect, _memmax, _heapgrow Functions, malloc Functions, realloc Functions 

Example: 
#include <stdio.h> 
#include <malloc.h> 
void main() 
 { 
  char *p; 
  char *fmt = "Memory available = %u\n"; 
  printf( fmt, _memavl() ); 
  _nheapgrow(); 
  printf( fmt, _memavl() ); 
  p = (char *) malloc( 2000 ); 
  printf( fmt, _memavl() ); 
 } 
produces the following: 
Memory available = 0 
Memory available = 62732 
Memory available = 60730 

Classification: WATCOM 

Systems: All


### memccpy, _fmemccpy

Synopsis: 
#include <string.h> 
void *memccpy( void *dest, const void *src, 
        int c, size_t cnt ); 
void __far *_fmemccpy( void __far *dest, 
            const void __far *src, 
            int c, size_t cnt ); 

Description: The memccpy and _fmemccpy functions copy bytes from src to dest up to and including the first occurrence of the character c or until cnt bytes have been copied, whichever comes first. 
The _fmemccpy function is a data model independent form of the memccpy function.  It accepts far pointer arguments and returns a far pointer.  It is most useful in mixed memory model applications. 

Returns: The memccpy and _fmemccpy functions return a pointer to the byte in dest following the character c if one is found and copied, otherwise it returns NULL. 

See Also: memcpy, memmove, memset 

Example: 
#include <stdio.h> 
#include <string.h> 
char *msg = "This is the string: not copied"; 
void main() 
 { 
  auto char buffer[80]; 
  memset( buffer, '\0', 80 ); 
  memccpy( buffer, msg, ':', 80 ); 
  printf( "%s\n", buffer ); 
 } 
produces the following: 
This is the string: 

Classification: WATCOM 

Systems:  memccpy - All 
_fmemccpy - All


### memchr, _fmemchr

Synopsis: 
#include <string.h> 
void *memchr( const void *buf, int ch, size_t length ); 
void __far *_fmemchr( const void __far *buf, 
           int ch, 
           size_t length ); 

Description: The memchr and _fmemchr functions locate the first occurrence of ch (converted to an unsigned char) in the first length characters of the object pointed to by buf. 
The _fmemchr function is a data model independent form of the memchr function.  It accepts far pointer arguments and returns a far pointer.  It is most useful in mixed memory model applications. 

Returns: The memchr and _fmemchr functions return a pointer to the located character, or NULL if the character does not occur in the object. 

See Also: memcmp, memcpy, memset 

Example: 
#include <stdio.h> 
#include <string.h> 
void main() 
 { 
  char buffer[80]; 
  char *where; 
  strcpy( buffer, "video x-rays" ); 
  where = (char *) memchr( buffer, 'x', 6 ); 
  if( where == NULL ) 
   printf( "'x' not found\n" ); 
  else 
   printf( "%s\n", where ); 
  where = (char *) memchr( buffer, 'r', 9 ); 
  if( where == NULL ) 
   printf( "'r' not found\n" ); 
  else 
   printf( "%s\n", where ); 
 } 

Classification: memchr is ANSI, _fmemchr is not ANSI 

Systems:  memchr - All 
_fmemchr - All


### memcmp, _fmemcmp

Synopsis: 
#include <string.h> 
int memcmp( const void *s1, 
      const void *s2, 
      size_t length ); 
int _fmemcmp( const void __far *s1, 
       const void __far *s2, 
       size_t length ); 

Description: The memcmp and _fmemcmp functions compare the first length characters of the object pointed to by s1 to the object pointed to by s2. 
The _fmemcmp function is a data model independent form of the memcmp function that accepts far pointer arguments.  It is most useful in mixed memory model applications. 

Returns: The memcmp and _fmemcmp functions return an integer less than, equal to, or greater than zero, indicating that the object pointed to by s1 is less than, equal to, or greater than the object pointed to by s2. 

See Also: memchr, memcpy, memicmp, memset 

Example: 
#include <stdio.h> 
#include <string.h> 
void main() 
 { 
  auto char buffer[80]; 
  strcpy( buffer, "world" ); 
  if( memcmp( buffer, "Hello ", 6 ) < 0 ) { 
   printf( "Less than\n" ); 
  } 
 } 

Classification: memcmp is ANSI, _fmemcmp is not ANSI 

Systems:  memcmp - All 
_fmemcmp - All


### memcpy, _fmemcpy

Synopsis: 
#include <string.h> 
void *memcpy( void *dst, 
       const void *src, 
       size_t length ); 
void __far *_fmemcpy( void __far *dst, 
           const void __far *src, 
           size_t length ); 

Description: The memcpy and _fmemcpy functions copy length characters from the buffer pointed to by src into the buffer pointed to by dst.  Copying of overlapping objects is not guaranteed to work properly.  See the  memmove function if you wish to copy objects that overlap. 
The _fmemcpy function is a data model independent form of the memcpy function.  It accepts far pointer arguments and returns a far pointer.  It is most useful in mixed memory model applications. 

Returns: The original value of dst is returned. 

See Also: memchr, memcmp, memmove, memset 

Example: 
#include <stdio.h> 
#include <string.h> 
void main() 
 { 
  auto char buffer[80]; 
  memcpy( buffer, "Hello", 5 ); 
  buffer[5] = '\0'; 
  printf( "%s\n", buffer ); 
 } 

Classification: memcpy is ANSI, _fmemcpy is not ANSI 

Systems:  memcpy - All 
_fmemcpy - All


### memicmp, _fmemicmp

Synopsis: 
#include <string.h> 
int memicmp( const void *s1, 
       const void *s2, 
       size_t length ); 
int _fmemicmp( const void __far *s1, 
        const void __far *s2, 
        size_t length ); 

Description: The memicmp and _fmemicmp functions compare, with case insensitivity (upper- and lowercase characters are equivalent), the first length characters of the object pointed to by s1 to the object pointed to by s2. 
The _fmemicmp function is a data model independent form of the memicmp function that accepts far pointer arguments.  It is most useful in mixed memory model applications. 

Returns: The memicmp and _fmemicmp functions return an integer less than, equal to, or greater than zero, indicating that the object pointed to by s1 is less than, equal to, or greater than the object pointed to by s2. 

See Also: memchr, memcmp, memcpy, memset 

Example: 
#include <stdio.h> 
#include <string.h> 
void main() 
 { 
  char buffer[80]; 
  if( memicmp( buffer, "Hello", 5 ) < 0 ) { 
   printf( "Less than\n" ); 
  } 
 } 

Classification: WATCOM 

Systems:  memicmp - All 
_fmemicmp - All


### _memmax

Synopsis: 
#include <malloc.h> 
size_t _memmax( void ); 

Description: The _memmax function returns the size of the largest contiguous block of memory available for dynamic memory allocation in the near heap (the default data segment).  In the tiny, small and medium memory models, the default data segment is only extended as needed to satisfy requests for memory allocation.  Therefore, you will need to call  _nheapgrow in these memory models before calling _memmax in order to get a meaningful result. 

Returns: The _memmax function returns the size of the largest contiguous block of memory available for dynamic memory allocation in the near heap.  If 0 is returned, then there is no more memory available in the near heap. 

See Also: calloc, _freect, _memavl, _heapgrow, malloc 

Example: 
#include <stdio.h> 
#include <malloc.h> 
void main() 
 { 
  char *p; 
  size_t size; 
  size = _memmax(); 
  printf( "Maximum memory available is %u\n", size ); 
  _nheapgrow(); 
  size = _memmax(); 
  printf( "Maximum memory available is %u\n", size ); 
  p = (char *) _nmalloc( size ); 
  size = _memmax(); 
  printf( "Maximum memory available is %u\n", size ); 
 } 
produces the following: 
Maximum memory available is 0 
Maximum memory available is 62700 
Maximum memory available is 0 

Classification: WATCOM 

Systems: All


### memmove, _fmemmove

Synopsis: 
#include <string.h> 
void *memmove( void *dst, 
        const void *src, 
        size_t length ); 
void __far *_fmemmove( void __far *dst, 
            const void __far *src, 
            size_t length ); 

Description: The memmove and _fmemmove functions copy length characters from the buffer pointed to by src to the buffer pointed to by dst.  Copying of overlapping objects will take place properly.  See the  memcpy or  _fmemcpy functions to copy objects that do not overlap. 
The _fmemmove function is a data model independent form of the memmove function.  It accepts far pointer arguments and returns a far pointer.  It is most useful in mixed memory model applications. 

Returns: The memmove and _fmemmove functions return dst. 

See Also: memcpy, memset 

Example: 
#include <string.h> 
void main() 
 { 
  char buffer[80]; 
  memmove( buffer+1, buffer, 79 ); 
  buffer[0] = '*'; 
 } 

Classification: memmove is ANSI, _fmemmove is not ANSI 

Systems:  memmove - All 
_fmemmove - All


### memset, _fmemset

Synopsis: 
#include <string.h> 
void *memset( void *dst, 
       int c, 
       size_t length ); 
void __far *_fmemset( void __far *dst, 
           int c, 
           size_t length ); 

Description: The memset and _fmemset functions fill the first length characters of the object pointed to by s with the value c. 
The _fmemset function is a data model independent form of the memset function.  It accepts far pointer arguments and returns a far pointer.  It is most useful in mixed memory model applications. 

Returns: The memset and _fmemset functions return the pointer s. 

See Also: memchr, memcmp, memcpy, memmove 

Example: 
#include <string.h> 
void main() 
 { 
  char buffer[80]; 
  memset( buffer, '=', 80 ); 
 } 

Classification: memset is ANSI, _fmemset is not ANSI 

Systems:  memset - All 
_fmemset - All


### min

Synopsis: 
#include <stdlib.h> 
#define min(a,b)  (((a) < (b)) ? (a) : (b)) 

Description: The min macro will evaluate to be the lesser of two values.  It is implemented as follows. 
    
   #define min(a,b)  (((a) < (b)) ? (a) : (b)) 

Returns: The min macro will evaluate to the smaller of the two values passed. 

See Also: max 

Example: 
#include <stdio.h> 
#include <stdlib.h> 
void main() 
 { 
  int a; 
  /* 
   * The following line will set the variable "a" to 1 
   * since 10 is greater than 1. 
   */ 
  a = min( 1, 10 ); 
  printf( "The value is: %d\n", a ); 
 } 

Classification: WATCOM 

Systems: All


### mkdir

Synopsis: 
#include <sys\types.h> 
#include <direct.h> 
int mkdir( const char *path ); 

Description: The mkdir function creates a new subdirectory with name path.  The path can be either relative to the current working directory or it can be an absolute path name. 

Returns: The mkdir function returns zero if successful, and a non-zero value otherwise. 

Errors: When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

EACCES Search permission is denied for a component of path or write permission is denied on the parent directory of the directory to be created. 

ENOENT The specified path does not exist or path is an empty string. 

See Also: chdir, chmod, getcwd, rmdir, stat, umask 

Example: 
To make a new directory called \watcom on drive C: 
#include <sys\types.h> 
#include <direct.h> 
void main() 
 { 
  mkdir( "c:\\watcom" ); 
 } 
Note the use of two adjacent backslash characters (\) within character-string constants to signify a single backslash. 

Classification: POSIX 1003.1 

Systems: All


### MK_FP

Synopsis: 
#include <i86.h> 
void __far *MK_FP( unsigned int segment, 
          unsigned int offset ); 

Description: The MK_FP macro can be used to obtain the far pointer value given by the segment segment value and the offset offset value.  These values may be obtained by using the  FP_SEG and  FP_OFF macros. 

Returns: The macro returns a far pointer. 

See Also: FP_OFF, FP_SEG, segread 

Example: 
#include <i86.h> 
#include <stdio.h> 
void main() 
 { 
  unsigned short __far *bios_prtr_port_1; 
  bios_prtr_port_1 = 
      (unsigned short __far *) MK_FP( 0x40, 0x8 ); 
  printf( "Port address is %x\n", *bios_prtr_port_1 ); 
 } 

Classification: Intel 

Systems: MACRO


### mktime

Synopsis: 
#include <time.h> 
time_t mktime( struct tm *timeptr ); 
struct  tm { 
 int tm_sec;  /* seconds after the minute -- [0,61] */ 
 int tm_min;  /* minutes after the hour  -- [0,59] */ 
 int tm_hour;  /* hours after midnight   -- [0,23] */ 
 int tm_mday;  /* day of the month     -- [1,31] */ 
 int tm_mon;  /* months since January   -- [0,11] */ 
 int tm_year;  /* years since 1900          */ 
 int tm_wday;  /* days since Sunday     -- [0,6]  */ 
 int tm_yday;  /* days since January 1   -- [0,365]*/ 
 int tm_isdst; /* Daylight Savings Time flag */ 
}; 

Description: The  mktime function converts the local time information in the structure pointed to by timeptr into a calendar time (Coordinated Universal Time) with the same encoding used by the  time function.  The original values of the fields  tm_sec,  tm_min,  tm_hour,  tm_mday, and  tm_mon are not restricted to ranges described for  struct tm.  If these fields are not in their proper ranges, they are adjusted so that they are in the proper ranges.  Values for the fields  tm_wday and  tm_yday are computed after all the other fields have been adjusted. 
If the original value of  tm_isdst is negative, this field is computed also.  Otherwise, a value of 0 is treated as "daylight savings time is not in effect" and a positive value is treated as "daylight savings time is in effect". 
Whenever mktime is called, the  tzset function is also called. 

Returns: The  mktime function returns the converted calendar time. 

See Also: asctime, clock, ctime, difftime, gmtime, localtime, strftime, time, tzset 

Example: 
#include <stdio.h> 
#include <time.h> 
static const char *week_day[] = { 
  "Sunday", "Monday", "Tuesday", "Wednesday", 
  "Thursday", "Friday", "Saturday" 
}; 
void main() 
 { 
  struct tm new_year; 
  new_year.tm_year  = 2001 - 1900; 
  new_year.tm_mon  = 0; 
  new_year.tm_mday  = 1; 
  new_year.tm_hour  = 0; 
  new_year.tm_min  = 0; 
  new_year.tm_sec  = 0; 
  new_year.tm_isdst = 0; 
  mktime( &new_year ); 
  printf( "The next century begins on a %s\n", 
       week_day[ new_year.tm_wday ] ); 
 } 
produces the following: 
The next century begins on a Monday 

Classification: ANSI 

Systems: All


### modf

Synopsis: 
#include <math.h> 
double modf( double value, double *iptr ); 

Description: The modf function breaks the argument value into integral and fractional parts, each of which has the same sign as the argument.  It stores the integral part as a double in the object pointed to by iptr. 

Returns: The modf function returns the signed fractional part of value. 

See Also: frexp, ldexp 

Example: 
#include <stdio.h> 
#include <math.h> 
void main() 
 { 
  double integral_value, fractional_part; 
  fractional_part = modf( 4.5, &integral_value ); 
  printf( "%f %f\n", fractional_part, integral_value ); 
  fractional_part = modf( -4.5, &integral_value ); 
  printf( "%f %f\n", fractional_part, integral_value ); 
 } 
produces the following: 
0.500000 4.000000 
-0.500000 -4.000000 

Classification: ANSI 

Systems: All


### movedata

Synopsis: 
#include <string.h> 
void movedata( unsigned int src_segment, 
        unsigned int src_offset, 
        unsigned int tgt_segment, 
        unsigned int tgt_offset, 
        size_t length ); 

Description: The movedata function copies length bytes from the far pointer calculated as (src_segment:src_offset) to a target location determined as a far pointer (tgt_segment:tgt_offset). 
Overlapping data may not be correctly copied.  When the source and target areas may overlap, copy the areas one character at a time. 
The function is useful to move data when the near address(es) of the source and/or target areas are not known. 

Returns: No value is returned. 

See Also: FP_SEG, FP_OFF, memcpy, segread 

Example: 
#include <stdio.h> 
#include <string.h> 
#include <dos.h> 
void main() 
 { 
  char buffer[14] = { 
    '*', 0x17, 'H', 0x17, 'e', 0x17, 'l', 0x17, 
    'l', 0x17, 'o', 0x17, '*', 0x17 }; 
  movedata( FP_SEG( buffer ), 
       FP_OFF( buffer ), 
       0xB800, 
       0x0720, 
       14 ); 
 } 

Classification: WATCOM 

Systems: All


### _moveto, _moveto_w

Synopsis: 
#include <graph.h> 
struct xycoord _FAR _moveto( short x, short y ); 
struct _wxycoord _FAR _moveto_w( double x, double y ); 

Description: The _moveto functions set the current output position for graphics.  The _moveto function uses the view coordinate system.  The _moveto_w function uses the window coordinate system. 
The current output position is set to be the point at the coordinates (x,y).  Nothing is drawn by the function.  The  _lineto function uses the current output position as the starting point when a line is drawn. 
Note that the output position for graphics output differs from that for text output.  The output position for text output can be set by use of the  _settextposition function. 

Returns: The _moveto functions return the previous value of the output position for graphics. 

See Also: _getcurrentposition, _lineto, _settextposition 

Example: 
#include <conio.h> 
#include <graph.h> 
main() 
{ 
  _setvideomode( _VRES16COLOR ); 
  _moveto( 100, 100 ); 
  _lineto( 540, 100 ); 
  _lineto( 320, 380 ); 
  _lineto( 100, 100 ); 
  getch(); 
  _setvideomode( _DEFAULTMODE ); 
} 

Classification: PC Graphics 

Systems:  _moveto - DOS, QNX 
_moveto_w - DOS, QNX


### _msize Functions

Synopsis: 
#include <malloc.h> 
size_t _msize( void *buffer ); 
size_t _bmsize( __segment seg, void __based(void) *buffer ); 
size_t _fmsize( void __far *buffer ); 
size_t _nmsize( void __near *buffer ); 

Description: The  _msize functions return the size of the memory block pointed to by buffer that was allocated by a call to the appropriate version of the  calloc,  malloc, or  realloc functions. 
You must use the correct  _msize function as listed below depending on which heap the memory block belongs to. 

_msize Depends on data model of the program 

_bmsize Based heap specified by seg value 

_fmsize Far heap (outside the default data segment) 

_nmsize Near heap (inside the default data segment) 
In small data models (small and medium memory models),  _msize maps to  _nmsize.  In large data models (compact, large and huge memory models),  _msize maps to  _fmsize. 

Returns: The  _msize functions return the size of the memory block pointed to by buffer. 

See Also: calloc Functions, _expand Functions, free Functions, halloc, hfree, malloc Functions, realloc Functions, sbrk 

Example: 
#include <stdio.h> 
#include <malloc.h> 
void main() 
 { 
  void *buffer; 
  buffer = malloc( 999 ); 
  printf( "Size of block is %u bytes\n", 
        _msize( buffer ) ); 
 } 
produces the following: 
Size of block is 1000 bytes 

Classification: WATCOM 

Systems:  _msize - All 
_bmsize - DOS/16, Win/16, QNX/16, OS/2 1.x(all) 
_fmsize - DOS/16, Win/16, QNX/16, OS/2 1.x(all) 
_nmsize - DOS, Win, QNX, OS/2 1.x, OS/2 1.x(MT), OS/2 2.x, NT


### nosound

Synopsis: 
#include <i86.h> 
void nosound( void ); 

Description: The nosound function turns off the PC's speaker. 

Returns: The nosound function has no return value. 

See Also: delay, sound 

Example: 
#include <i86.h> 
void main() 
 { 
  sound( 200 ); 
  delay( 500 );  /* delay for 1/2 second */ 
  nosound(); 
 } 

Classification: Intel 

Systems: DOS, Win, QNX


### offsetof

Synopsis: 
#include <stddef.h> 
size_t offsetof( composite, name ); 

Description: The offsetof macro returns the offset of the element name within the  struct or  union composite.  This provides a portable method to determine the offset. 

Returns: The offsetof function returns the offset of name. 

Example: 
#include <stdio.h> 
#include <stddef.h> 
struct new_def 
{  char *first; 
  char second[10]; 
  int third; 
}; 
void main() 
 { 
  printf( "first:%d second:%d third:%d\n", 
    offsetof( struct new_def, first ), 
    offsetof( struct new_def, second ), 
    offsetof( struct new_def, third ) ); 
 } 
produces the following: 
In a small data model, the following would result: 
first:0 second:2 third:12 
In a large data model, the following would result: 
first:0 second:4 third:14 

Classification: ANSI 

Systems: MACRO


### onexit

Synopsis: 
#include <stdlib.h> 
onexit_t onexit( onexit_t func ) 

Description: The onexit function is passed the address of function func to be called when the program terminates normally.  Successive calls to onexit create a list of functions that will be executed on a "last-in, first-out" basis.  No more than 32 functions can be registered with the onexit function. 
The functions have no parameters and do not return values. 
NOTE:  The onexit function is not an ANSI function.  The ANSI standard function  atexit does the same thing that onexit does and should be used instead of onexit where ANSI portability is concerned. 

Returns: The onexit function returns func if the registration succeeds, NULL if it fails. 

See Also: abort, atexit, exit, _exit 

Example: 
#include <stdio.h> 
#include <stdlib.h> 
void main() 
 { 
  void func1(void), func2(void), func3(void); 
  onexit( func1 ); 
  onexit( func2 ); 
  onexit( func3 ); 
  printf( "Do this first.\n" ); 
 } 
void func1(void) { printf( "last.\n" ); } 
void func2(void) { printf( "this " ); } 
void func3(void) { printf( "Do " ); } 
produces the following: 
Do this first. 
Do this last. 

Classification: WATCOM 

Systems: All


### open

Synopsis: 
#include <sys\types.h> 
#include <sys\stat.h> 
#include <fcntl.h> 
int open( const char *path, int access, ... ); 

Description: The open function opens a file at the operating system level.  The name of the file to be opened is given by path.  The file will be accessed according to the access mode specified by access.  The optional argument is the file permissions to be used when the  O_CREAT flag is on in the access mode. 
The access mode is established by a combination of the bits defined in the <fcntl.h> header file.  The following bits may be set: 

O_RDONLY permit the file to be only read. 

O_WRONLY permit the file to be only written. 

O_RDWR permit the file to be both read and written. 

O_APPEND causes each record that is written to be written at the end of the file. 

O_CREAT has no effect when the file indicated by filename already exists; otherwise, the file is created; 

O_TRUNC causes the file to be truncated to contain no data when the file exists; has no effect when the file does not exist. 

O_BINARY causes the file to be opened in binary mode which means that data will be transmitted to and from the file unchanged. 

O_TEXT causes the file to be opened in text mode which means that carriage-return characters are written before any linefeed character that is written and causes carriage-return characters to be removed when encountered during reads. 

O_NOINHERIT indicates that this file is not to be inherited by a child process. 

O_EXCL indicates that this file is to be opened for exclusive access.  If the file exists and  O_CREAT was also specified then the open will fail (i.e., use  O_EXCL to ensure that the file does not already exist). 
When neither  O_TEXT nor  O_BINARY are specified, the default value in the global variable  _fmode is used to set the file translation mode.  When the program begins execution, this variable has a value of  O_TEXT. 
 O_CREAT must be specified when the file does not exist and it is to be written. 
When the file is to be created ( O_CREAT is specified), an additional argument must be passed which contains the file permissions to be used for the new file.  The access permissions for the file or directory are specified as a combination of bits (defined in the <sys\stat.h> header file). 
The following bits define permissions for the owner. 

S_IRWXU Read, write, execute/search 

S_IRUSR Read permission 

S_IWUSR Write permission 

S_IXUSR Execute/search permission 
The following bits define permissions for the group. 

S_IRWXG Read, write, execute/search 

S_IRGRP Read permission 

S_IWGRP Write permission 

S_IXGRP Execute/search permission 
The following bits define permissions for others. 

S_IRWXO Read, write, execute/search 

S_IROTH Read permission 

S_IWOTH Write permission 

S_IXOTH Execute/search permission 
The following bits define miscellaneous permissions used by other implementations. 

S_IREAD is equivalent to S_IRUSR (read permission) 

S_IWRITE is equivalent to S_IWUSR (write permission) 

S_IEXEC is equivalent to S_IXUSR (execute/search permission) 
All files are readable with DOS; however, it is a good idea to set S_IREAD when read permission is intended for the file. 
The open function applies the current file permission mask to the specified permissions (see  umask). 

Returns: If successful, open returns a handle for the file.  When an error occurs while opening the file, -1 is returned. 

Errors: When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

EACCES Access denied because path specifies a directory or a volume ID, or attempting to open a read-only file for writing 

EMFILE No more handles available (too many open files) 

ENOENT Path or file not found 

See Also: chsize, close, creat, dup, dup2, eof, exec Functions, filelength, fileno, fstat, isatty, lseek, read, setmode, sopen, stat, tell, write, umask 

Example: 
#include <sys\stat.h> 
#include <sys\types.h> 
#include <fcntl.h> 
void main() 
 { 
  int handle; 
  /* open a file for output          */ 
  /* replace existing file if it exists    */ 
  handle = open( "file", 
        O_WRONLY | O_CREAT | O_TRUNC, 
        S_IRUSR | S_IWUSR | S_IRGRP | S_IWGRP ); 
  /* read a file which is assumed to exist  */ 
  handle = open( "file", O_RDONLY ); 
  /* append to the end of an existing file  */ 
  /* write a new file if file does not exist */ 
  handle = open( "file", 
        O_WRONLY | O_CREAT | O_APPEND, 
        S_IRUSR | S_IWUSR | S_IRGRP | S_IWGRP ); 
 } 

Classification: POSIX 1003.1 

Systems: All


### opendir

Synopsis: 
#include <direct.h> 
DIR *opendir( const char *dirname ); 

Description: The opendir function is used in conjunction with the functions  readdir and  closedir to obtain the list of file names contained in the directory specified by dirname.  The path indicated by dirname can be either relative to the current working directory or it can be an absolute path name.  As an extension to POSIX, the last part of dirname can contain the characters '?' and '*' for matching multiple files within a directory. 
The file <direct.h> contains definitions for the structure  dirent. 
typedef struct dirent { 
  char   d_dta[ 21 ];    /* disk transfer area */ 
  char   d_attr;       /* file's attribute */ 
  unsigned short int d_time; /* file's time */ 
  unsigned short int d_date; /* file's date */ 
  long   d_size;       /* file's size */ 
  char   d_name[ 13 ];    /* file's name */ 
  ino_t  d_ino;       /* serial number */ 
  char   d_first;      /* flag for 1st time */ 
} DIR; 
More than one directory can be read at the same time using the  opendir,  readdir, and  closedir functions. 

Returns: The opendir function, if successful, returns a pointer to a structure required for subsequent calls to  readdir to retrieve the file names matching the pattern specified by dirname.  The opendir function returns NULL if dirname is not a valid pathname, or if there are no files matching dirname. 

Errors: When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

EACCES Search permission is denied for a component of dirname or read permission is denied for dirname. 

ENOENT The named directory does not exist. 

See Also: closedir, _dos_find Functions, readdir 

Example: 
To get a list of files contained in the directory \watcom\h on your default disk: 
#include <stdio.h> 
#include <direct.h> 
void main() 
 { 
  DIR *dirp; 
  struct dirent *direntp; 
  dirp = opendir( "\\watcom\\h" ); 
  if( dirp == NULL ) { 
   perror( "" ); 
  } else { 
   for(;;) { 
    direntp = readdir( dirp ); 
    if( direntp == NULL ) break; 
    printf( "%s\n", direntp->d_name ); 
   } 
   closedir( dirp ); 
  } 
 } 
Note the use of two adjacent backslash characters (\) within character-string constants to signify a single backslash. 

Classification: POSIX 1003.1 

Systems: All


### _os_handle

Synopsis: 
#include <io.h> 
int _os_handle( int handle ); 

Description: The _os_handle function takes a POSIX-style file handle specified by handle.  It returns the corresponding operating system level handle. 

Returns: The _os_handle function returns the operating system handle that corresponds to the specified POSIX-style file handle. 

See Also: _hdopen, close, fdopen, open 

Example: 
#include <stdio.h> 
#include <io.h> 
void main() 
 { 
  int handle; 
  FILE *fp; 
  fp = fopen( "file", "r" ); 
  if( fp != NULL ) { 
   handle = _os_handle( fileno( fp ) ); 
   fclose( fp ); 
  } 
 } 

Classification: WATCOM 

Systems: DOS, Win, OS/2 1.x(all), OS/2 2.x, NT


### _outgtext

Synopsis: 
#include <graph.h> 
void _FAR _outgtext( char _FAR *text ); 

Description: The _outgtext function displays the character string indicated by the argument text.  The string must be terminated by a null character ('\0'). 
The string is displayed starting at the current position (see the  _moveto function) in the current color and in the currently selected font (see the  _setfont function).  The current position is updated to follow the displayed text. 
When no font has been previously selected with  _setfont, a default font will be used.  The default font is an 8-by-8 bit-mapped font. 
The graphics library can display text in three different ways. 

 1.The  _outtext and  _outmem functions can be used in any video mode.  However, this variety of text can be displayed in only one size. 

 2.The  _grtext function displays text as a sequence of line segments, and can be drawn in different sizes, with different orientations and alignments. 

 3.The  _outgtext function displays text in the currently selected font.  Both bit-mapped and vector fonts are supported; the size and type of text depends on the fonts that are available. 

Returns: The _outgtext function does not return a value. 

See Also: _registerfonts, _unregisterfonts, _setfont, _getfontinfo, _getgtextextent, _setgtextvector, _getgtextvector, _outtext, _outmem, _grtext 

Example: 
#include <conio.h> 
#include <stdio.h> 
#include <graph.h> 
main() 
{ 
  int i, n; 
  char buf[ 10 ]; 
  _setvideomode( _VRES16COLOR ); 
  n = _registerfonts( "*.fon" ); 
  for( i = 0; i < n; ++i ) { 
    sprintf( buf, "n%d", i ); 
    _setfont( buf ); 
    _moveto( 100, 100 ); 
    _outgtext( "WATCOM Graphics" ); 
    getch(); 
    _clearscreen( _GCLEARSCREEN ); 
  } 
  _unregisterfonts(); 
  _setvideomode( _DEFAULTMODE ); 
} 

Classification: PC Graphics 

Systems: DOS, QNX


### _outmem

Synopsis: 
#include <graph.h> 
void _FAR _outmem( char _FAR *text, short length ); 

Description: The _outmem function displays the character string indicated by the argument text.  The argument length specifies the number of characters to be displayed.  Unlike the  _outtext function, _outmem will display the graphical representation of characters such as ASCII 10 and 0, instead of interpreting them as control characters. 
The text is displayed using the current text color (see the  _settextcolor function), starting at the current text position (see the  _settextposition function).  The text position is updated to follow the end of the displayed text. 
The graphics library can display text in three different ways. 

 1.The  _outtext and  _outmem functions can be used in any video mode.  However, this variety of text can be displayed in only one size. 

 2.The  _grtext function displays text as a sequence of line segments, and can be drawn in different sizes, with different orientations and alignments. 

 3.The  _outgtext function displays text in the currently selected font.  Both bit-mapped and vector fonts are supported; the size and type of text depends on the fonts that are available. 

Returns: The _outmem function does not return a value. 

See Also: _settextcolor, _settextposition, _settextwindow, _grtext, _outtext, _outgtext 

Example: 
#include <conio.h> 
#include <graph.h> 
main() 
{ 
  int i; 
  char buf[ 1 ]; 
  _clearscreen( _GCLEARSCREEN ); 
  for( i = 0; i <= 255; ++i ) { 
    _settextposition( 1 + i % 16, 
             1 + 5 * ( i / 16 ) ); 
    buf[ 0 ] = i; 
    _outmem( buf, 1 ); 
  } 
  getch(); 
} 

Classification: PC Graphics 

Systems: DOS, QNX


### outp

Synopsis: 
#include <conio.h> 
unsigned int outp( int port, int value ); 

Description: The outp function writes one byte, determined by value, to the 80x86 hardware port whose number is given by port. 
A hardware port is used to communicate with a device.  One or two bytes can be read and/or written from each port, depending upon the hardware.  Consult the technical documentation for your computer to determine the port numbers for a device and the expected usage of each port for a device. 

Returns: The value transmitted is returned. 

See Also: inp, inpd, inpw, outpd, outpw 

Example: 
#include <conio.h> 
void main() 
 { 
  /* turn off speaker */ 
  outp( 0x61, inp( 0x61 ) & 0xFC ); 
 } 

Classification: Intel 

Systems: All


### outpd

Synopsis: 
#include <conio.h> 
unsigned long outpd( int port, 
          unsigned long value ); 

Description: The outpd function writes a double-word (four bytes), determined by value, to the 80x86 hardware port whose number is given by port. 
A hardware port is used to communicate with a device.  One or two bytes can be read and/or written from each port, depending upon the hardware.  Consult the technical documentation for your computer to determine the port numbers for a device and the expected usage of each port for a device. 

Returns: The value transmitted is returned. 

See Also: inp, inpd, inpw, outp, outpw 

Example: 
#include <conio.h> 
#define DEVICE 34 
void main() 
 { 
  outpd( DEVICE, 0x12345678 ); 
 } 

Classification: Intel 

Systems: DOS/32, Win/32, QNX/32, OS/2 2.x, NT


### outpw

Synopsis: 
#include <conio.h> 
unsigned int outpw( int port, 
          unsigned int value ); 

Description: The outpw function writes a word (two bytes), determined by value, to the 80x86 hardware port whose number is given by port. 
A hardware port is used to communicate with a device.  One or two bytes can be read and/or written from each port, depending upon the hardware.  Consult the technical documentation for your computer to determine the port numbers for a device and the expected usage of each port for a device. 

Returns: The value transmitted is returned. 

See Also: inp, inpd, inpw, outp, outpd 

Example: 
#include <conio.h> 
#define DEVICE 34 
void main() 
 { 
  outpw( DEVICE, 0x1234 ); 
 } 

Classification: Intel 

Systems: All


### _outtext

Synopsis: 
#include <graph.h> 
void _FAR _outtext( char _FAR *text ); 

Description: The _outtext function displays the character string indicated by the argument text.  The string must be terminated by a null character ('\0').  When a line-feed character ('\n') is encountered in the string, the characters following will be displayed on the next row of the screen. 
The text is displayed using the current text color (see the  _settextcolor function), starting at the current text position (see the  _settextposition function).  The text position is updated to follow the end of the displayed text. 
The graphics library can display text in three different ways. 

 1.The  _outtext and  _outmem functions can be used in any video mode.  However, this variety of text can be displayed in only one size. 

 2.The  _grtext function displays text as a sequence of line segments, and can be drawn in different sizes, with different orientations and alignments. 

 3.The  _outgtext function displays text in the currently selected font.  Both bit-mapped and vector fonts are supported; the size and type of text depends on the fonts that are available. 

Returns: The _outtext function does not return a value. 

See Also: _settextcolor, _settextposition, _settextwindow, _grtext, _outmem, _outgtext 

Example: 
#include <conio.h> 
#include <graph.h> 
main() 
{ 
  _setvideomode( _TEXTC80 ); 
  _settextposition( 10, 30 ); 
  _outtext( "WATCOM Graphics" ); 
  getch(); 
  _setvideomode( _DEFAULTMODE ); 
} 

Classification: PC Graphics 

Systems: DOS, QNX


### perror

Synopsis: 
#include <stdio.h> 
void perror( const char *prefix ); 

Description: The  perror function prints, on the file designated by  stderr, the error message corresponding to the error number contained in  errno.  The  perror function writes first the string pointed to by prefix to stderr.  This is followed by a colon (":"), a space, the string returned by strerror(errno), and a newline character. 

Returns: The  perror function returns no value.  Because the function uses the  fprintf function,  errno can be set when an error is detected during the execution of that function. 

See Also: strerror 

Example: 
#include <stdio.h> 
void main() 
 { 
  FILE *fp; 
  fp = fopen( "data.fil", "r" ); 
  if( fp == NULL ) { 
    perror( "Unable to open file" ); 
  } 
 } 

Classification: ANSI 

Systems: All


### _pg_analyzechart, _pg_analyzechartms

Synopsis: 
#include <pgchart.h> 
short _FAR _pg_analyzechart( chartenv _FAR *env, 
               char _FAR * _FAR *cat, 
               float _FAR *values, short n ); 
short _FAR _pg_analyzechartms( chartenv _FAR *env, 
                char _FAR * _FAR *cat, 
                float _FAR *values, 
                short nseries, 
                short n, short dim, 
                char _FAR * _FAR *labels ); 

Description: The _pg_analyzechart functions analyze either a single-series or a multi-series bar, column or line chart.  These functions calculate default values for chart elements without actually displaying the chart. 
The _pg_analyzechart function analyzes a single-series bar, column or line chart.  The chart environment structure env is filled with default values based on the type of chart and the values of the cat and values arguments.  The arguments are the same as for the  _pg_chart function. 
The _pg_analyzechartms function analyzes a multi-series bar, column or line chart.  The chart environment structure env is filled with default values based on the type of chart and the values of the cat, values and labels arguments.  The arguments are the same as for the  _pg_chartms function. 

Returns: The _pg_analyzechart functions return zero if successful; otherwise, a non-zero value is returned. 

See Also: _pg_defaultchart, _pg_initchart, _pg_chart, _pg_chartpie, _pg_chartscatter, _pg_analyzepie, _pg_analyzescatter 

Example: 
#include <graph.h> 
#include <pgchart.h> 
#include <string.h> 
#include <conio.h> 
#define NUM_VALUES 4 
char _FAR *categories[ NUM_VALUES ] = { 
  "Jan", "Feb", "Mar", "Apr" 
}; 
float values[ NUM_VALUES ] = { 
  20, 45, 30, 25 
}; 
main() 
{ 
  chartenv env; 
  _setvideomode( _VRES16COLOR ); 
  _pg_initchart(); 
  _pg_defaultchart( &env, 
           _PG_COLUMNCHART, _PG_PLAINBARS ); 
  strcpy( env.maintitle.title, "Column Chart" ); 
  _pg_analyzechart( &env, 
           categories, values, NUM_VALUES ); 
  /* use manual scaling */ 
  env.yaxis.autoscale = 0; 
  env.yaxis.scalemin = 0.0; 
  env.yaxis.scalemax = 100.0; 
  env.yaxis.ticinterval = 25.0; 
  _pg_chart( &env, categories, values, NUM_VALUES ); 
  getch(); 
  _setvideomode( _DEFAULTMODE ); 
} 

Classification: PC Graphics 

Systems:  _pg_analyzechart - DOS, QNX 
_pg_analyzechartms - DOS, QNX


### _pg_analyzepie

Synopsis: 
#include <pgchart.h> 
short _FAR _pg_analyzepie( chartenv _FAR *env, 
              char _FAR * _FAR *cat, 
              float _FAR *values, 
              short _FAR *explode, short n ); 

Description: The _pg_analyzepie function analyzes a pie chart. This function calculates default values for chart elements without actually displaying the chart. 
The chart environment structure env is filled with default values based on the values of the cat, values and explode arguments.  The arguments are the same as for the  _pg_chartpie function. 

Returns: The _pg_analyzepie function returns zero if successful; otherwise, a non-zero value is returned. 

See Also: _pg_defaultchart, _pg_initchart, _pg_chart, _pg_chartpie, _pg_chartscatter, _pg_analyzechart, _pg_analyzescatter 

Example: 
#include <graph.h> 
#include <pgchart.h> 
#include <string.h> 
#include <conio.h> 
#define NUM_VALUES 4 
char _FAR *categories[ NUM_VALUES ] = { 
  "Jan", "Feb", "Mar", "Apr" 
}; 
float values[ NUM_VALUES ] = { 
  20, 45, 30, 25 
}; 
short explode[ NUM_VALUES ] = { 
  1, 0, 0, 0 
}; 
main() 
{ 
  chartenv env; 
  _setvideomode( _VRES16COLOR ); 
  _pg_initchart(); 
  _pg_defaultchart( &env, 
           _PG_PIECHART, _PG_NOPERCENT ); 
  strcpy( env.maintitle.title, "Pie Chart" ); 
  env.legend.place = _PG_BOTTOM; 
  _pg_analyzepie( &env, categories, 
          values, explode, NUM_VALUES ); 
  /* make legend window same width as data window */ 
  env.legend.autosize = 0; 
  env.legend.legendwindow.x1 = env.datawindow.x1; 
  env.legend.legendwindow.x2 = env.datawindow.x2; 
  _pg_chartpie( &env, categories, 
         values, explode, NUM_VALUES ); 
  getch(); 
  _setvideomode( _DEFAULTMODE ); 
} 

Classification: PC Graphics 

Systems: DOS, QNX


### _pg_analyzescatter, _pg_analyzescatterms

Synopsis: 
#include <pgchart.h> 
short _FAR _pg_analyzescatter( chartenv _FAR *env, 
                float _FAR *x, 
                float _FAR *y, short n ); 
short _FAR _pg_analyzescatterms( 
           chartenv _FAR *env, 
           float _FAR *x, float _FAR *y, 
           short nseries, short n, short dim, 
           char _FAR * _FAR *labels ); 

Description: The _pg_analyzescatter functions analyze either a single-series or a multi-series scatter chart.  These functions calculate default values for chart elements without actually displaying the chart. 
The _pg_analyzescatter function analyzes a single-series scatter chart.  The chart environment structure env is filled with default values based on the values of the x and y arguments.  The arguments are the same as for the  _pg_chartscatter function. 
The _pg_analyzescatterms function analyzes a multi-series scatter chart.  The chart environment structure env is filled with default values based on the values of the x, y and labels arguments.  The arguments are the same as for the  _pg_chartscatterms function. 

Returns: The _pg_analyzescatter functions return zero if successful; otherwise, a non-zero value is returned. 

See Also: _pg_defaultchart, _pg_initchart, _pg_chart, _pg_chartpie, _pg_chartscatter, _pg_analyzechart, _pg_analyzepie 

Example: 
#include <graph.h> 
#include <pgchart.h> 
#include <string.h> 
#include <conio.h> 
#define NUM_VALUES 4 
#define NUM_SERIES 2 
char _FAR *labels[ NUM_SERIES ] = { 
  "Jan", "Feb" 
}; 
float x[ NUM_SERIES ][ NUM_VALUES ] = { 
  5, 15, 30, 40, 10, 20, 30, 45 
}; 
float y[ NUM_SERIES ][ NUM_VALUES ] = { 
  10, 15, 30, 45, 40, 30, 15, 5 
}; 
main() 
{ 
  chartenv env; 
  _setvideomode( _VRES16COLOR ); 
  _pg_initchart(); 
  _pg_defaultchart( &env, 
           _PG_SCATTERCHART, _PG_POINTANDLINE ); 
  strcpy( env.maintitle.title, "Scatter Chart" ); 
  _pg_analyzescatterms( &env, x, y, NUM_SERIES, 
             NUM_VALUES, NUM_VALUES, labels ); 
  /* display x-axis labels with 2 decimal places */ 
  env.xaxis.autoscale = 0; 
  env.xaxis.ticdecimals = 2; 
  _pg_chartscatterms( &env, x, y, NUM_SERIES, 
            NUM_VALUES, NUM_VALUES, labels ); 
  getch(); 
  _setvideomode( _DEFAULTMODE ); 
} 

Classification: PC Graphics 

Systems:  _pg_analyzescatter - DOS, QNX 
_pg_analyzescatterms - DOS, QNX


### _pg_chart, _pg_chartms

Synopsis: 
#include <pgchart.h> 
short _FAR _pg_chart( chartenv _FAR *env, 
           char _FAR * _FAR *cat, 
           float _FAR *values, short n ); 
short _FAR _pg_chartms( chartenv _FAR *env, 
            char _FAR * _FAR *cat, 
            float _FAR *values, short nseries, 
            short n, short dim, 
            char _FAR * _FAR *labels ); 

Description: The _pg_chart functions display either a single-series or a multi-series bar, column or line chart.  The type of chart displayed and other chart options are contained in the env argument.  The argument cat is an array of strings.  These strings describe the categories against which the data in the values array is charted. 
The _pg_chart function displays a bar, column or line chart from the single series of data contained in the values array.  The argument n specifies the number of values to chart. 
The _pg_chartms function displays a multi-series bar, column or line chart.  The argument nseries specifies the number of series of data to chart.  The argument values is assumed to be a two-dimensional array defined as follows: 
    
   float values[ nseries ][ dim ]; 
The number of values used from each series is given by the argument n, where n is less than or equal to dim.  The argument labels is an array of strings.  These strings describe each of the series and are used in the chart legend. 

Returns: The _pg_chart functions return zero if successful; otherwise, a non-zero value is returned. 

See Also: _pg_defaultchart, _pg_initchart, _pg_chartpie, _pg_chartscatter, _pg_analyzechart, _pg_analyzepie, _pg_analyzescatter 

Example: 
#include <graph.h> 
#include <pgchart.h> 
#include <string.h> 
#include <conio.h> 
#define NUM_VALUES 4 
char _FAR *categories[ NUM_VALUES ] = { 
  "Jan", "Feb", "Mar", "Apr" 
}; 
float values[ NUM_VALUES ] = { 
  20, 45, 30, 25 
}; 
main() 
{ 
  chartenv env; 
  _setvideomode( _VRES16COLOR ); 
  _pg_initchart(); 
  _pg_defaultchart( &env, 
           _PG_COLUMNCHART, _PG_PLAINBARS ); 
  strcpy( env.maintitle.title, "Column Chart" ); 
  _pg_chart( &env, categories, values, NUM_VALUES ); 
  getch(); 
  _setvideomode( _DEFAULTMODE ); 
} 
produces the following: 
The graphical image cannot be reproduced here. See the printed 
version of the manual. 

Classification: PC Graphics 

Systems:  _pg_chart - DOS, QNX 
_pg_chartms - DOS, QNX


### _pg_chartpie

Synopsis: 
#include <pgchart.h> 
short _FAR _pg_chartpie( chartenv _FAR *env, 
             char _FAR * _FAR *cat, 
             float _FAR *values, 
             short _FAR *explode, short n ); 

Description: The _pg_chartpie function displays a pie chart.  The chart is displayed using the options specified in the env argument. 
The pie chart is created from the data contained in the values array.  The argument n specifies the number of values to chart. 
The argument cat is an array of strings.  These strings describe each of the pie slices and are used in the chart legend.  The argument explode is an array of values corresponding to each of the pie slices.  For each non-zero element in the array, the corresponding pie slice is drawn "exploded", or slightly offset from the rest of the pie. 

Returns: The _pg_chartpie function returns zero if successful; otherwise, a non-zero value is returned. 

See Also: _pg_defaultchart, _pg_initchart, _pg_chart, _pg_chartscatter, _pg_analyzechart, _pg_analyzepie, _pg_analyzescatter 

Example: 
#include <graph.h> 
#include <pgchart.h> 
#include <string.h> 
#include <conio.h> 
#define NUM_VALUES 4 
char _FAR *categories[ NUM_VALUES ] = { 
  "Jan", "Feb", "Mar", "Apr" 
}; 
float values[ NUM_VALUES ] = { 
  20, 45, 30, 25 
}; 
short explode[ NUM_VALUES ] = { 
  1, 0, 0, 0 
}; 
main() 
{ 
  chartenv env; 
  _setvideomode( _VRES16COLOR ); 
  _pg_initchart(); 
  _pg_defaultchart( &env, 
           _PG_PIECHART, _PG_NOPERCENT ); 
  strcpy( env.maintitle.title, "Pie Chart" ); 
  _pg_chartpie( &env, categories, 
         values, explode, NUM_VALUES ); 
  getch(); 
  _setvideomode( _DEFAULTMODE ); 
} 
produces the following: 
The graphical image cannot be reproduced here. See the printed 
version of the manual. 

Classification: PC Graphics 

Systems: DOS, QNX


### _pg_chartscatter, _pg_chartscatterms

Synopsis: 
#include <pgchart.h> 
short _FAR _pg_chartscatter( chartenv _FAR *env, 
               float _FAR *x, 
               float _FAR *y, short n ); 
short _FAR _pg_chartscatterms( chartenv _FAR *env, 
                float _FAR *x, 
                float _FAR *y, 
                short nseries, 
                short n, short dim, 
                char _FAR * _FAR *labels ); 

Description: The _pg_chartscatter functions display either a single-series or a multi-series scatter chart.  The chart is displayed using the options specified in the env argument. 
The _pg_chartscatter function displays a scatter chart from the single series of data contained in the arrays x and y.  The argument n specifies the number of values to chart. 
The _pg_chartscatterms function displays a multi-series scatter chart.  The argument nseries specifies the number of series of data to chart.  The arguments x and y are assumed to be two-dimensional arrays defined as follows: 
    
   float x[ nseries ][ dim ]; 
The number of values used from each series is given by the argument n, where n is less than or equal to dim.  The argument labels is an array of strings.  These strings describe each of the series and are used in the chart legend. 

Returns: The _pg_chartscatter functions return zero if successful; otherwise, a non-zero value is returned. 

See Also: _pg_defaultchart, _pg_initchart, _pg_chart, _pg_chartpie, _pg_analyzechart, _pg_analyzepie, _pg_analyzescatter 

Example: 
#include <graph.h> 
#include <pgchart.h> 
#include <string.h> 
#include <conio.h> 
#define NUM_VALUES 4 
#define NUM_SERIES 2 
char _FAR *labels[ NUM_SERIES ] = { 
  "Jan", "Feb" 
}; 
float x[ NUM_SERIES ][ NUM_VALUES ] = { 
  5, 15, 30, 40, 10, 20, 30, 45 
}; 
float y[ NUM_SERIES ][ NUM_VALUES ] = { 
  10, 15, 30, 45, 40, 30, 15, 5 
}; 
main() 
{ 
  chartenv env; 
  _setvideomode( _VRES16COLOR ); 
  _pg_initchart(); 
  _pg_defaultchart( &env, 
           _PG_SCATTERCHART, _PG_POINTANDLINE ); 
  strcpy( env.maintitle.title, "Scatter Chart" ); 
  _pg_chartscatterms( &env, x, y, NUM_SERIES, 
            NUM_VALUES, NUM_VALUES, labels ); 
  getch(); 
  _setvideomode( _DEFAULTMODE ); 
} 
produces the following: 
The graphical image cannot be reproduced here. See the printed 
version of the manual. 

Classification: PC Graphics 

Systems:  _pg_chartscatter - DOS, QNX 
_pg_chartscatterms - DOS, QNX


### _pg_defaultchart

Synopsis: 
#include <pgchart.h> 
short _FAR _pg_defaultchart( chartenv _FAR *env, 
               short type, short style ); 

Description: The _pg_defaultchart function initializes the chart structure env to contain default values before a chart is drawn.  All values in the chart structure are initialized, including blanking of all titles.  The chart type in the structure is initialized to the value type, and the chart style is initialized to style. 
The argument type can have one of the following values: 

_PG_BARCHART Bar chart (horizontal bars) 

_PG_COLUMNCHART Column chart (vertical bars) 

_PG_LINECHART Line chart 

_PG_SCATTERCHART Scatter chart 

_PG_PIECHART Pie chart 
Each type of chart can be drawn in one of two styles.  For each chart type the argument style can have one of the following values: 
    
   Type       Style 1         Style 2 
   Bar       _PG_PLAINBARS      _PG_STACKEDBARS 
   Column      _PG_PLAINBARS      _PG_STACKEDBARS 
   Line       _PG_POINTANDLINE     _PG_POINTONLY 
   Scatter     _PG_POINTANDLINE     _PG_POINTONLY 
   Pie       _PG_PERCENT       _PG_NOPERCENT 
For single-series bar and column charts, the chart style is ignored.  The "plain" (clustered) and "stacked" styles only apply when there is more than one series of data.  The "percent" style for pie charts causes percentages to be displayed beside each of the pie slices. 

Returns: The _pg_defaultchart function returns zero if successful; otherwise, a non-zero value is returned. 

See Also: _pg_initchart, _pg_chart, _pg_chartpie, _pg_chartscatter 

Example: 
#include <graph.h> 
#include <pgchart.h> 
#include <string.h> 
#include <conio.h> 
#define NUM_VALUES 4 
char _FAR *categories[ NUM_VALUES ] = { 
  "Jan", "Feb", "Mar", "Apr" 
}; 
float values[ NUM_VALUES ] = { 
  20, 45, 30, 25 
}; 
main() 
{ 
  chartenv env; 
  _setvideomode( _VRES16COLOR ); 
  _pg_initchart(); 
  _pg_defaultchart( &env, 
           _PG_COLUMNCHART, _PG_PLAINBARS ); 
  strcpy( env.maintitle.title, "Column Chart" ); 
  _pg_chart( &env, categories, values, NUM_VALUES ); 
  getch(); 
  _setvideomode( _DEFAULTMODE ); 
} 

Classification: PC Graphics 

Systems: DOS, QNX


### _pg_getchardef

Synopsis: 
#include <pgchart.h> 
short _FAR _pg_getchardef( short ch, 
              unsigned char _FAR *def ); 

Description: The _pg_getchardef function retrieves the current bit-map definition for the character ch.  The bit-map is placed in the array def.  The current font must be an 8-by-8 bit-mapped font. 

Returns: The _pg_getchardef function returns zero if successful; otherwise, a non-zero value is returned. 

See Also: _pg_defaultchart, _pg_initchart, _pg_chart, _pg_chartpie, _pg_chartscatter, _pg_setchardef 

Example: 
#include <graph.h> 
#include <pgchart.h> 
#include <string.h> 
#include <conio.h> 
#define NUM_VALUES 4 
float x[ NUM_VALUES ] = { 
  5, 25, 45, 65 
}; 
float y[ NUM_VALUES ] = { 
  5, 45, 25, 65 
}; 
char diamond[ 8 ] = { 
  0x10, 0x28, 0x44, 0x82, 0x44, 0x28, 0x10, 0x00 
}; 
main() 
{ 
  chartenv env; 
  char old_def[ 8 ]; 
  _setvideomode( _VRES16COLOR ); 
  _pg_initchart(); 
  _pg_defaultchart( &env, 
           _PG_SCATTERCHART, _PG_POINTANDLINE ); 
  strcpy( env.maintitle.title, "Scatter Chart" ); 
  /* change asterisk character to diamond */ 
  _pg_getchardef( '*', old_def ); 
  _pg_setchardef( '*', diamond ); 
  _pg_chartscatter( &env, x, y, NUM_VALUES ); 
  _pg_setchardef( '*', old_def ); 
  getch(); 
  _setvideomode( _DEFAULTMODE ); 
} 

Classification: PC Graphics 

Systems: DOS, QNX


### _pg_getpalette

Synopsis: 
#include <pgchart.h> 
short _FAR _pg_getpalette( paletteentry _FAR *pal ); 

Description: The _pg_getpalette function retrieves the internal palette of the presentation graphics system.  The palette controls the colors, line styles, fill patterns and plot characters used to display each series of data in a chart. 
The argument pal is an array of palette structures that will contain the palette.  Each element of the palette is a structure containing the following fields: 

color color used to display series 

style line style used for line and scatter charts 

fill fill pattern used to fill interior of bar and pie sections 

plotchar character plotted on line and scatter charts 

Returns: The _pg_getpalette function returns zero if successful; otherwise, a non-zero value is returned. 

See Also: _pg_defaultchart, _pg_initchart, _pg_chart, _pg_chartpie, _pg_chartscatter, _pg_setpalette, _pg_resetpalette 

Example: 
#include <graph.h> 
#include <pgchart.h> 
#include <string.h> 
#include <conio.h> 
#define NUM_VALUES 4 
char _FAR *categories[ NUM_VALUES ] = { 
  "Jan", "Feb", "Mar", "Apr" 
}; 
float values[ NUM_VALUES ] = { 
  20, 45, 30, 25 
}; 
char bricks[ 8 ] = { 
  0xff, 0x80, 0x80, 0x80, 0xff, 0x08, 0x08, 0x08 
}; 
main() 
{ 
  chartenv env; 
  palettetype pal; 
  _setvideomode( _VRES16COLOR ); 
  _pg_initchart(); 
  _pg_defaultchart( &env, 
           _PG_COLUMNCHART, _PG_PLAINBARS ); 
  strcpy( env.maintitle.title, "Column Chart" ); 
  /* get default palette and change 1st entry */ 
  _pg_getpalette( &pal ); 
  pal[ 1 ].color = 12; 
  memcpy( pal[ 1 ].fill, bricks, 8 ); 
  /* use new palette */ 
  _pg_setpalette( &pal ); 
  _pg_chart( &env, categories, values, NUM_VALUES ); 
  /* reset palette to default */ 
  _pg_resetpalette(); 
  getch(); 
  _setvideomode( _DEFAULTMODE ); 
} 

Classification: PC Graphics 

Systems: DOS, QNX


### _pg_getstyleset

Synopsis: 
#include <pgchart.h> 
void _FAR _pg_getstyleset( unsigned short _FAR *style ); 

Description: The _pg_getstyleset function retrieves the internal style-set of the presentation graphics system.  The style-set is a set of line styles used for drawing window borders and grid-lines.  The argument style is an array that will contain the style-set. 

Returns: The _pg_getstyleset function does not return a value. 

See Also: _pg_defaultchart, _pg_initchart, _pg_chart, _pg_chartpie, _pg_chartscatter, _pg_setstyleset, _pg_resetstyleset 

Example: 
#include <graph.h> 
#include <pgchart.h> 
#include <string.h> 
#include <conio.h> 
#define NUM_VALUES 4 
char _FAR *categories[ NUM_VALUES ] = { 
  "Jan", "Feb", "Mar", "Apr" 
}; 
float values[ NUM_VALUES ] = { 
  20, 45, 30, 25 
}; 
main() 
{ 
  chartenv env; 
  styleset style; 
  _setvideomode( _VRES16COLOR ); 
  _pg_initchart(); 
  _pg_defaultchart( &env, 
           _PG_COLUMNCHART, _PG_PLAINBARS ); 
  strcpy( env.maintitle.title, "Column Chart" ); 
  /* turn on yaxis grid, and use style 2 */ 
  env.yaxis.grid = 1; 
  env.yaxis.gridstyle = 2; 
  /* get default style-set and change entry 2 */ 
  _pg_getstyleset( &style ); 
  style[ 2 ] = 0x8888; 
  /* use new style-set */ 
  _pg_setstyleset( &style ); 
  _pg_chart( &env, categories, values, NUM_VALUES ); 
  /* reset style-set to default */ 
  _pg_resetstyleset(); 
  getch(); 
  _setvideomode( _DEFAULTMODE ); 
} 

Classification: PC Graphics 

Systems: DOS, QNX


### _pg_hlabelchart

Synopsis: 
#include <pgchart.h> 
short _FAR _pg_hlabelchart( chartenv _FAR *env, 
              short x, short y, 
              short color, 
              char _FAR *label ); 

Description: The _pg_hlabelchart function displays the text string label on the chart described by the env chart structure.  The string is displayed horizontally starting at the point (x,y), relative to the upper left corner of the chart.  The color specifies the palette color used to display the string. 

Returns: The _pg_hlabelchart function returns zero if successful; otherwise, a non-zero value is returned. 

See Also: _pg_defaultchart, _pg_initchart, _pg_chart, _pg_chartpie, _pg_chartscatter, _pg_vlabelchart 

Example: 
#include <graph.h> 
#include <pgchart.h> 
#include <string.h> 
#include <conio.h> 
#define NUM_VALUES 4 
char _FAR *categories[ NUM_VALUES ] = { 
  "Jan", "Feb", "Mar", "Apr" 
}; 
float values[ NUM_VALUES ] = { 
  20, 45, 30, 25 
}; 
main() 
{ 
  chartenv env; 
  _setvideomode( _VRES16COLOR ); 
  _pg_initchart(); 
  _pg_defaultchart( &env, 
           _PG_COLUMNCHART, _PG_PLAINBARS ); 
  strcpy( env.maintitle.title, "Column Chart" ); 
  _pg_chart( &env, categories, values, NUM_VALUES ); 
  _pg_hlabelchart( &env, 64, 32, 1, "Horizontal label" ); 
  _pg_vlabelchart( &env, 48, 32, 1, "Vertical label" ); 
  getch(); 
  _setvideomode( _DEFAULTMODE ); 
} 

Classification: PC Graphics 

Systems: DOS, QNX


### _pg_initchart

Synopsis: 
#include <pgchart.h> 
short _FAR _pg_initchart( void ); 

Description: The _pg_initchart function initializes the presentation graphics system.  This includes initializing the internal palette and style-set used when drawing charts.  This function must be called before any of the other presentation graphics functions. 
The initialization of the presentation graphics system requires that a valid graphics mode has been selected.  For this reason the  _setvideomode function must be called before _pg_initchart is called.  If a font has been selected (with the  _setfont function), that font will be used when text is displayed in a chart.  Font selection should also be done before initializing the presentation graphics system. 

Returns: The _pg_initchart function returns zero if successful; otherwise, a non-zero value is returned. 

See Also: _pg_defaultchart, _pg_chart, _pg_chartpie, _pg_chartscatter, _setvideomode, _setfont, _registerfonts 

Example: 
#include <graph.h> 
#include <pgchart.h> 
#include <string.h> 
#include <conio.h> 
#define NUM_VALUES 4 
char _FAR *categories[ NUM_VALUES ] = { 
  "Jan", "Feb", "Mar", "Apr" 
}; 
float values[ NUM_VALUES ] = { 
  20, 45, 30, 25 
}; 
main() 
{ 
  chartenv env; 
  _setvideomode( _VRES16COLOR ); 
  _pg_initchart(); 
  _pg_defaultchart( &env, 
           _PG_COLUMNCHART, _PG_PLAINBARS ); 
  strcpy( env.maintitle.title, "Column Chart" ); 
  _pg_chart( &env, categories, values, NUM_VALUES ); 
  getch(); 
  _setvideomode( _DEFAULTMODE ); 
} 

Classification: PC Graphics 

Systems: DOS, QNX


### _pg_resetpalette

Synopsis: 
#include <pgchart.h> 
short _FAR _pg_resetpalette( void ); 

Description: The _pg_resetpalette function resets the internal palette of the presentation graphics system to default values.  The palette controls the colors, line styles, fill patterns and plot characters used to display each series of data in a chart.  The default palette chosen is dependent on the current video mode. 

Returns: The _pg_resetpalette function returns zero if successful; otherwise, a non-zero value is returned. 

See Also: _pg_defaultchart, _pg_initchart, _pg_chart, _pg_chartpie, _pg_chartscatter, _pg_getpalette, _pg_setpalette 

Example: 
#include <graph.h> 
#include <pgchart.h> 
#include <string.h> 
#include <conio.h> 
#define NUM_VALUES 4 
char _FAR *categories[ NUM_VALUES ] = { 
  "Jan", "Feb", "Mar", "Apr" 
}; 
float values[ NUM_VALUES ] = { 
  20, 45, 30, 25 
}; 
char bricks[ 8 ] = { 
  0xff, 0x80, 0x80, 0x80, 0xff, 0x08, 0x08, 0x08 
}; 
main() 
{ 
  chartenv env; 
  palettetype pal; 
  _setvideomode( _VRES16COLOR ); 
  _pg_initchart(); 
  _pg_defaultchart( &env, 
           _PG_COLUMNCHART, _PG_PLAINBARS ); 
  strcpy( env.maintitle.title, "Column Chart" ); 
  /* get default palette and change 1st entry */ 
  _pg_getpalette( &pal ); 
  pal[ 1 ].color = 12; 
  memcpy( pal[ 1 ].fill, bricks, 8 ); 
  /* use new palette */ 
  _pg_setpalette( &pal ); 
  _pg_chart( &env, categories, values, NUM_VALUES ); 
  /* reset palette to default */ 
  _pg_resetpalette(); 
  getch(); 
  _setvideomode( _DEFAULTMODE ); 
} 

Classification: PC Graphics 

Systems: DOS, QNX


### _pg_resetstyleset

Synopsis: 
#include <pgchart.h> 
void _FAR _pg_resetstyleset( void ); 

Description: The _pg_resetstyleset function resets the internal style-set of the presentation graphics system to default values.  The style-set is a set of line styles used for drawing window borders and grid-lines. 

Returns: The _pg_resetstyleset function does not return a value. 

See Also: _pg_defaultchart, _pg_initchart, _pg_chart, _pg_chartpie, _pg_chartscatter, _pg_getstyleset, _pg_setstyleset 

Example: 
#include <graph.h> 
#include <pgchart.h> 
#include <string.h> 
#include <conio.h> 
#define NUM_VALUES 4 
char _FAR *categories[ NUM_VALUES ] = { 
  "Jan", "Feb", "Mar", "Apr" 
}; 
float values[ NUM_VALUES ] = { 
  20, 45, 30, 25 
}; 
main() 
{ 
  chartenv env; 
  styleset style; 
  _setvideomode( _VRES16COLOR ); 
  _pg_initchart(); 
  _pg_defaultchart( &env, 
           _PG_COLUMNCHART, _PG_PLAINBARS ); 
  strcpy( env.maintitle.title, "Column Chart" ); 
  /* turn on yaxis grid, and use style 2 */ 
  env.yaxis.grid = 1; 
  env.yaxis.gridstyle = 2; 
  /* get default style-set and change entry 2 */ 
  _pg_getstyleset( &style ); 
  style[ 2 ] = 0x8888; 
  /* use new style-set */ 
  _pg_setstyleset( &style ); 
  _pg_chart( &env, categories, values, NUM_VALUES ); 
  /* reset style-set to default */ 
  _pg_resetstyleset(); 
  getch(); 
  _setvideomode( _DEFAULTMODE ); 
} 

Classification: PC Graphics 

Systems: DOS, QNX


### _pg_setchardef

Synopsis: 
#include <pgchart.h> 
short _FAR _pg_setchardef( short ch, 
              unsigned char _FAR *def ); 

Description: The _pg_setchardef function sets the current bit-map definition for the character ch.  The bit-map is contained in the array def.  The current font must be an 8-by-8 bit-mapped font. 

Returns: The _pg_setchardef function returns zero if successful; otherwise, a non-zero value is returned. 

See Also: _pg_defaultchart, _pg_initchart, _pg_chart, _pg_chartpie, _pg_chartscatter, _pg_getchardef 

Example: 
#include <graph.h> 
#include <pgchart.h> 
#include <string.h> 
#include <conio.h> 
#define NUM_VALUES 4 
float x[ NUM_VALUES ] = { 
  5, 25, 45, 65 
}; 
float y[ NUM_VALUES ] = { 
  5, 45, 25, 65 
}; 
char diamond[ 8 ] = { 
  0x10, 0x28, 0x44, 0x82, 0x44, 0x28, 0x10, 0x00 
}; 
main() 
{ 
  chartenv env; 
  char old_def[ 8 ]; 
  _setvideomode( _VRES16COLOR ); 
  _pg_initchart(); 
  _pg_defaultchart( &env, 
           _PG_SCATTERCHART, _PG_POINTANDLINE ); 
  strcpy( env.maintitle.title, "Scatter Chart" ); 
  /* change asterisk character to diamond */ 
  _pg_getchardef( '*', old_def ); 
  _pg_setchardef( '*', diamond ); 
  _pg_chartscatter( &env, x, y, NUM_VALUES ); 
  _pg_setchardef( '*', old_def ); 
  getch(); 
  _setvideomode( _DEFAULTMODE ); 
} 

Classification: PC Graphics 

Systems: DOS, QNX


### _pg_setpalette

Synopsis: 
#include <pgchart.h> 
short _FAR _pg_setpalette( paletteentry _FAR *pal ); 

Description: The _pg_setpalette function sets the internal palette of the presentation graphics system.  The palette controls the colors, line styles, fill patterns and plot characters used to display each series of data in a chart. 
The argument pal is an array of palette structures containing the new palette.  Each element of the palette is a structure containing the following fields: 

color color used to display series 

style line style used for line and scatter charts 

fill fill pattern used to fill interior of bar and pie sections 

plotchar character plotted on line and scatter charts 

Returns: The _pg_setpalette function returns zero if successful; otherwise, a non-zero value is returned. 

See Also: _pg_defaultchart, _pg_initchart, _pg_chart, _pg_chartpie, _pg_chartscatter, _pg_getpalette, _pg_resetpalette 

Example: 
#include <graph.h> 
#include <pgchart.h> 
#include <string.h> 
#include <conio.h> 
#define NUM_VALUES 4 
char _FAR *categories[ NUM_VALUES ] = { 
  "Jan", "Feb", "Mar", "Apr" 
}; 
float values[ NUM_VALUES ] = { 
  20, 45, 30, 25 
}; 
char bricks[ 8 ] = { 
  0xff, 0x80, 0x80, 0x80, 0xff, 0x08, 0x08, 0x08 
}; 
main() 
{ 
  chartenv env; 
  palettetype pal; 
  _setvideomode( _VRES16COLOR ); 
  _pg_initchart(); 
  _pg_defaultchart( &env, 
           _PG_COLUMNCHART, _PG_PLAINBARS ); 
  strcpy( env.maintitle.title, "Column Chart" ); 
  /* get default palette and change 1st entry */ 
  _pg_getpalette( &pal ); 
  pal[ 1 ].color = 12; 
  memcpy( pal[ 1 ].fill, bricks, 8 ); 
  /* use new palette */ 
  _pg_setpalette( &pal ); 
  _pg_chart( &env, categories, values, NUM_VALUES ); 
  /* reset palette to default */ 
  _pg_resetpalette(); 
  getch(); 
  _setvideomode( _DEFAULTMODE ); 
} 

Classification: PC Graphics 

Systems: DOS, QNX


### _pg_setstyleset

Synopsis: 
#include <pgchart.h> 
void _FAR _pg_setstyleset( unsigned short _FAR *style ); 

Description: The _pg_setstyleset function retrieves the internal style-set of the presentation graphics system.  The style-set is a set of line styles used for drawing window borders and grid-lines.  The argument style is an array containing the new style-set. 

Returns: The _pg_setstyleset function does not return a value. 

See Also: _pg_defaultchart, _pg_initchart, _pg_chart, _pg_chartpie, _pg_chartscatter, _pg_getstyleset, _pg_resetstyleset 

Example: 
#include <graph.h> 
#include <pgchart.h> 
#include <string.h> 
#include <conio.h> 
#define NUM_VALUES 4 
char _FAR *categories[ NUM_VALUES ] = { 
  "Jan", "Feb", "Mar", "Apr" 
}; 
float values[ NUM_VALUES ] = { 
  20, 45, 30, 25 
}; 
main() 
{ 
  chartenv env; 
  styleset style; 
  _setvideomode( _VRES16COLOR ); 
  _pg_initchart(); 
  _pg_defaultchart( &env, 
           _PG_COLUMNCHART, _PG_PLAINBARS ); 
  strcpy( env.maintitle.title, "Column Chart" ); 
  /* turn on yaxis grid, and use style 2 */ 
  env.yaxis.grid = 1; 
  env.yaxis.gridstyle = 2; 
  /* get default style-set and change entry 2 */ 
  _pg_getstyleset( &style ); 
  style[ 2 ] = 0x8888; 
  /* use new style-set */ 
  _pg_setstyleset( &style ); 
  _pg_chart( &env, categories, values, NUM_VALUES ); 
  /* reset style-set to default */ 
  _pg_resetstyleset(); 
  getch(); 
  _setvideomode( _DEFAULTMODE ); 
} 

Classification: PC Graphics 

Systems: DOS, QNX


### _pg_vlabelchart

Synopsis: 
#include <pgchart.h> 
short _FAR _pg_vlabelchart( chartenv _FAR *env, 
              short x, short y, 
              short color, 
              char _FAR *label ); 

Description: The _pg_vlabelchart function displays the text string label on the chart described by the env chart structure.  The string is displayed vertically starting at the point (x,y), relative to the upper left corner of the chart.  The color specifies the palette color used to display the string. 

Returns: The _pg_vlabelchart function returns zero if successful; otherwise, a non-zero value is returned. 

See Also: _pg_defaultchart, _pg_initchart, _pg_chart, _pg_chartpie, _pg_chartscatter, _pg_hlabelchart 

Example: 
#include <graph.h> 
#include <pgchart.h> 
#include <string.h> 
#include <conio.h> 
#define NUM_VALUES 4 
char _FAR *categories[ NUM_VALUES ] = { 
  "Jan", "Feb", "Mar", "Apr" 
}; 
float values[ NUM_VALUES ] = { 
  20, 45, 30, 25 
}; 
main() 
{ 
  chartenv env; 
  _setvideomode( _VRES16COLOR ); 
  _pg_initchart(); 
  _pg_defaultchart( &env, 
           _PG_COLUMNCHART, _PG_PLAINBARS ); 
  strcpy( env.maintitle.title, "Column Chart" ); 
  _pg_chart( &env, categories, values, NUM_VALUES ); 
  _pg_hlabelchart( &env, 64, 32, 1, "Horizontal label" ); 
  _pg_vlabelchart( &env, 48, 32, 1, "Vertical label" ); 
  getch(); 
  _setvideomode( _DEFAULTMODE ); 
} 

Classification: PC Graphics 

Systems: DOS, QNX


### _pie, _pie_w, _pie_wxy

Synopsis: 
#include <graph.h> 
short _FAR _pie( short fill, short x1, short y1, 
               short x2, short y2, 
               short x3, short y3, 
               short x4, short y4 ); 
short _FAR _pie_w( short fill, double x1, double y1, 
                double x2, double y2, 
                double x3, double y3, 
                double x4, double y4 ); 
short _FAR _pie_wxy( short fill, 
           struct _wxycoord _FAR *p1, 
           struct _wxycoord _FAR *p2, 
           struct _wxycoord _FAR *p3, 
           struct _wxycoord _FAR *p4 ); 

Description: The _pie functions draw pie-shaped wedges.  The _pie function uses the view coordinate system.  The _pie_w and _pie_wxy functions use the window coordinate system. 
The pie wedges are drawn by drawing an elliptical arc (in the way described for the  _arc functions) and then joining the center of the rectangle that contains the ellipse to the two endpoints of the arc. 
The elliptical arc is drawn with its center at the center of the rectangle established by the points (x1,y1) and (x2,y2).  The arc is a segment of the ellipse drawn within this bounding rectangle.  The arc starts at the point on this ellipse that intersects the vector from the centre of the ellipse to the point (x3,y3).  The arc ends at the point on this ellipse that intersects the vector from the centre of the ellipse to the point (x4,y4).  The arc is drawn in a counter-clockwise direction with the current plot action using the current color and the current line style. 
The following picture illustrates the way in which the bounding rectangle and the vectors specifying the start and end points are defined. 
The graphical image cannot be reproduced here.  See the printed version of the manual. 
When the coordinates (x1,y1) and (x2,y2) establish a line or a point (this happens when one or more of the x-coordinates or y-coordinates are equal), nothing is drawn. 
The argument fill determines whether the figure is filled in or has only its outline drawn.  The argument can have one of two values: 

_GFILLINTERIOR fill the interior by writing pixels with the current plot action using the current color and the current fill mask 

_GBORDER leave the interior unchanged; draw the outline of the figure with the current plot action using the current color and line style 

Returns: The _pie functions return a non-zero value when the figure was successfully drawn; otherwise, zero is returned. 

See Also: _arc, _ellipse, _setcolor, _setfillmask, _setlinestyle, _setplotaction 

Example: 
#include <conio.h> 
#include <graph.h> 
main() 
{ 
  _setvideomode( _VRES16COLOR ); 
  _pie( _GBORDER, 120, 90, 520, 390, 
          140, 20, 190, 460 ); 
  getch(); 
  _setvideomode( _DEFAULTMODE ); 
} 
produces the following: 
The graphical image cannot be reproduced here. See the printed 
version of the manual. 

Classification: PC Graphics 

Systems:  _pie - DOS, QNX 
_pie_w - DOS, QNX 
_pie_wxy - DOS, QNX


### _polygon, _polygon_w, _polygon_wxy

Synopsis: 
#include <graph.h> 
short _FAR _polygon( short fill, short numpts, 
           struct xycoord _FAR *points ); 
short _FAR _polygon_w( short fill, short numpts, 
            double _FAR *points ); 
short _FAR _polygon_wxy( short fill, short numpts, 
             struct _wxycoord _FAR *points ); 

Description: The _polygon functions draw polygons.  The _polygon function uses the view coordinate system.  The _polygon_w and _polygon_wxy functions use the window coordinate system. 
The polygon is defined as containing numpts points whose coordinates are given in the array points. 
The argument fill determines whether the polygon is filled in or has only its outline drawn.  The argument can have one of two values: 

_GFILLINTERIOR fill the interior by writing pixels with the current plot action using the current color and the current fill mask 

_GBORDER leave the interior unchanged; draw the outline of the figure with the current plot action using the current color and line style 

Returns: The _polygon functions return a non-zero value when the polygon was successfully drawn; otherwise, zero is returned. 

See Also: _setcolor, _setfillmask, _setlinestyle, _setplotaction 

Example: 
#include <conio.h> 
#include <graph.h> 
struct xycoord points[ 5 ] = { 
  319, 140, 224, 209, 261, 320, 
  378, 320, 415, 209 
}; 
main() 
{ 
  _setvideomode( _VRES16COLOR ); 
  _polygon( _GBORDER, 5, &points ); 
  getch(); 
  _setvideomode( _DEFAULTMODE ); 
} 
produces the following: 
The graphical image cannot be reproduced here. See the printed 
version of the manual. 

Classification: PC Graphics 

Systems:  _polygon - DOS, QNX 
_polygon_w - DOS, QNX 
_polygon_wxy - DOS, QNX


### pow

Synopsis: 
#include <math.h> 
double pow( double x, double y ); 

Description: The  pow function computes x raised to the power y.  A domain error occurs if x is zero and y is less than or equal to 0, or if x is negative and y is not an integer.  A range error may occur. 

Returns: The  pow function returns the value of x raised to the power y.  When the argument is outside the permissible range, the  matherr function is called.  Unless the default  matherr function is replaced, it will set the global variable  errno to  EDOM, and print a "DOMAIN error" diagnostic message using the  stderr stream. 

See Also: exp, log, sqrt 

Example: 
#include <stdio.h> 
#include <math.h> 
void main() 
 { 
  printf( "%f\n", pow( 1.5, 2.5 ) ); 
 } 
produces the following: 
2.755676 

Classification: ANSI 

Systems: All


### printf

Synopsis: 
#include <stdio.h> 
int printf( const char *format, ... ); 

Description: The printf function writes output to the file designated by  stdout under control of the argument format.  The format string is described below. 

Returns: The printf function returns the number of characters written, or a negative value if an output error occurred.  When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

See Also: _bprintf, cprintf, fprintf, sprintf, _vbprintf, vcprintf, vfprintf, vprintf, vsprintf 

Example: 
#include <stdio.h> 
void main() 
 { 
  char *weekday, *month; 
  weekday = "Saturday"; 
  month = "April"; 
  printf( "%s, %s %d, %d\n", 
     weekday, month, 18, 1987 ); 
  printf( "f1 = %8.4f f2 = %10.2E x = %#08x i = %d\n", 
      23.45,    3141.5926,  0x1db,   -1 ); 
 } 
produces the following: 
Saturday, April 18, 1987 
f1 =  23.4500 f2 =  3.14E+003 x = 0x0001db i = -1 

Format Control String: The format control string consists of ordinary characters, that are written exactly as they occur in the format string, and conversion specifiers, that cause argument values to be written as they are encountered during the processing of the format string.  An ordinary character in the format string is any character, other than a percent character (%), that is not part of a conversion specifier.  A conversion specifier is a sequence of characters in the format string that begins with a percent character (%) and is followed, in sequence, by the following: 

ozero or more format control flags that can modify the final effect of the format directive 
oan optional decimal integer, or an asterisk character ('*'), that specifies a minimum field width to be reserved for the formatted item 
oan optional precision specification in the form of a period character (.), followed by an optional decimal integer or an asterisk character (*) 
oan optional type length specification:  one of "h", "l", "L", "w", "N" or "F" 
oa character that specifies the type of conversion to be performed:  one of the characters "cdeEfFgGinopsuxX". 
The valid format control flags are: 

"-" the formatted item is left-justified within the field; normally, items are right-justified 

"+" a signed, positive object will always start with a plus character (+); normally, only negative items begin with a sign 

" " a signed, positive object will always start with a space character; if both "+" and " " are specified, "+" overrides " " 

"#" an alternate conversion form is used: 

ofor "o" (unsigned octal) conversions, the precision is incremented, if necessary, so that the first digit is "0". 
ofor "x" or "X" (unsigned hexadecimal) conversions, a non-zero value is prepended with "0x" or "0X" respectively 
ofor "e", "E", "f", "g" or "G" (any floating-point) conversions, the result always contains a decimal-point character, even if no digits follow it; normally, a decimal-point character appears in the result only if there is a digit to follow it 
oin addition to the preceding, for "g" or "G" conversions, trailing zeros are not removed from the result 
If no field width is specified, or if the value that is given is less than the number of characters in the converted value (subject to any precision value), a field of sufficient width to contain the converted value is used.  If the converted value has fewer characters than are specified by the field width, the value is padded on the left (or right, subject to the left-justification flag) with spaces or zero characters ("0").  If the field width begins with a zero, the value is padded with zeros, otherwise the value is padded with spaces.  If the field width is "*", a value of type int from the argument list is used (before a precision argument or a conversion argument) as the minimum field width.  A negative field width value is interpreted as a left-justification flag, followed by a positive field width. 
As with the field width specifier, a precision specifier of "*" causes a value of type int from the argument list to be used as the precision specifier.  If no precision value is given, a precision of 0 is used.  The precision value affects the following conversions: 

ofor "d", "i", "o", "u", "x" and "X" (integer) conversions, the precision specifies the minimum number of digits to appear 
ofor "e", "E" and "f" (fixed-precision, floating-point) conversions, the precision specifies the number of digits to appear after the decimal-point character 
ofor "g" and "G" (variable-precision, floating-point) conversions, the precision specifies the maximum number of significant digits to appear 
ofor "s" (string) conversions, the precision specifies the maximum number of characters to appear 
A type length specifier affects the conversion as follows: 

o"h" causes a "d", "i", "o", "u", "x" or "X" (integer) format conversion to treat the argument as a short int or unsigned short int argument.  Note that, although the argument may have been promoted to an int as part of the function call, the value is converted to the smaller type before it is formatted. 
o"h" causes an "f" format conversion to interpret a long argument as a fixed-point number.  The value is formatted with the same rules as for floating-point values.  This is a WATCOM extension. 
o"h" causes an "n" (converted length assignment) operation to assign the converted length to an object of type unsigned short int 
o"h" causes an "s" operation to treat the input string as an ASCII character string composed of 8-bit characters. 
o"l" causes a "d", "i", "o", "u", "x" or "X" (integer) conversion to process a long int or unsigned long int argument; 
o"l" causes an "n" (converted length assignment) operation to assign the converted length to an object of type unsigned long int 
o"l" or "w" cause an "s" operation to treat the input string as a wide character string (a string composed of characters of type  wchar_t) or a 16-bit Unicode character string. 
o"F" causes the pointer associated with "n", "p", "s" conversions to be treated as a far pointer; 
o"L" causes an "e", "E", "f", "g", "G" (double) conversion to process a long double argument; 
o"N" causes the pointer associated with "n", "p", "s" conversions to be treated as a near pointer; 
The valid conversion type specifiers are: 

c An argument of type int is converted to a value of type char and the corresponding ASCII character code is written to the output stream. 

d, i An argument of type int is converted to a signed decimal notation and written to the output stream.  The default precision is 1, but if more digits are required, leading zeros are added. 

e, E An argument of type double is converted to a decimal notation in the form [-]d.ddde[+|-]ddd similar to FORTRAN exponential (E) notation.  The leading sign appears (subject to the format control flags) only if the argument is negative. If the argument is non-zero, the digit before the decimal-point character is non-zero.  The precision is used as the number of digits following the decimal-point character.  If the precision is not specified, a default precision of six is used.  If the precision is 0, the decimal-point character is suppressed.  The value is rounded to the appropriate number of digits.  For "E" conversions, the exponent begins with the character "E" rather than "e".  The exponent sign and a three-digit number (that indicates the power of ten by which the decimal fraction is multiplied) are always produced. 

f An argument of type double is converted to a decimal notation in the form [-]ddd.ddd similar to FORTRAN fixed-point (F) notation.  The leading sign appears (subject to the format control flags) only if the argument is negative. The precision is used as the number of digits following the decimal-point character.  If the precision is not specified, a default precision of six is used.  If the precision is 0, the decimal-point character is suppressed, otherwise, at least one digit is produced before the decimal-point character.  The value is rounded to the appropriate number of digits. 

g, G An argument of type double is converted using either the "f" or "e" (or "E", for a "G" conversion) style of conversion depending on the value of the argument.  In either case, the precision specifies the number of significant digits that are contained in the result.  "e" style conversion is used only if the exponent from such a conversion would be less than -4 or greater than the precision.  Trailing zeros are removed from the result and a decimal-point character only appears if it is followed by a digit. 

n The number of characters that have been written to the output stream is assigned to the integer pointed to by the argument.  No output is produced. 

o An argument of type int is converted to an unsigned octal notation and written to the output stream.  The default precision is 1, but if more digits are required, leading zeros are added. 

p, P An argument of type void * is converted to a value of type int and the value is formatted as for a hexadecimal ("x") conversion. 

s Characters from the string specified by an argument of type char *, up to, but not including the terminating null character ('\0'), are written to the output stream.  If a precision is specified, no more than that many characters are written. 

hs Characters from the string specified by an argument of type char *, up to, but not including the terminating null character ('\0'), are written to the output stream.  If a precision is specified, no more than that many characters are written (e.g., %.7ls). 

ls, ws Characters from the string specified by an argument of type wchar_t *, up to, but not including the terminating null character (L'\0'), are written to the output stream.  If a precision is specified, no more than that many characters are written (e.g., %.7ls). 

u An argument of type int is converted to an unsigned decimal notation and written to the output stream.  The default precision is 1, but if more digits are required, leading zeros are added. 

x, X An argument of type int is converted to an unsigned hexadecimal notation and written to the output stream.  The default precision is 1, but if more digits are required, leading zeros are added.  Hexadecimal notation uses the digits "0" through "9" and the characters "a" through "f" or "A" through "F" for "x" or "X" conversions respectively, as the hexadecimal digits.  Subject to the alternate-form control flag, "0x" or "0X" is prepended to the output. 
Any other conversion type specifier character, including another percent character (%), is written to the output stream with no special interpretation. 
The arguments must correspond with the conversion type specifiers, left to right in the string; otherwise, indeterminate results will occur. 
If the value corresponding to a floating-point specifier is infinity, or not a number (NAN), then the output will be "inf" or "-inf" for infinity, and "nan" or "-nan" for NAN's. 
For example, a specifier of the form "%8.*f" will define a field to be at least 8 characters wide, and will get the next argument for the precision to be used in the conversion. 

Classification: ANSI, (except for F and N modifiers) 

Systems: All


### putc

Synopsis: 
#include <stdio.h> 
int putc( int c, FILE *fp ); 

Description: The  putc function is equivalent to  fputc, except it may be implemented as a macro.  The  putc function writes the character specified by the argument c to the output stream designated by fp. 

Returns: The  putc function returns the character written. If a write error occurs, the error indicator is set and  putc returns  EOF.  When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

See Also: fopen, fputc, fputchar, fputs, putchar, puts, ferror 

Example: 
#include <stdio.h> 
void main() 
 { 
  FILE *fp; 
  int c; 
  fp = fopen( "file", "r" ); 
  if( fp != NULL ) { 
   while( (c = fgetc( fp )) != EOF ) 
     putc( c, stdout ); 
   fclose( fp ); 
  } 
 } 

Classification: ANSI 

Systems: All


### putch

Synopsis: 
#include <conio.h> 
int putch( int c ); 

Description: The putch function writes the character specified by the argument c to the console. 

Returns: The putch function returns the character written. 

See Also: getch, getche, kbhit, ungetch 

Example: 
#include <conio.h> 
#include <stdio.h> 
void main() 
 { 
  FILE *fp; 
  int c; 
  fp = fopen( "file", "r" ); 
  if ( fp != NULL ) { 
   while( (c = fgetc( fp )) != EOF ) 
    putch( c ); 
  } 
  fclose( fp ); 
 } 

Classification: WATCOM 

Systems: All


### putchar

Synopsis: 
#include <stdio.h> 
int putchar( int c ); 

Description: The putchar function writes the character specified by the argument c to the output stream  stdout. 
The function is equivalent to 
    
   fputc( c, stdout ); 

Returns: The putchar function returns the character written.  If a write error occurs, the error indicator is set and putchar returns  EOF.  When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

See Also: fputc, fputchar, fputs, putc 

Example: 
#include <stdio.h> 
void main() 
 { 
  FILE *fp; 
  int c; 
  fp = fopen( "file", "r" ); 
  c = fgetc( fp ); 
  while( c != EOF ) { 
    putchar( c ); 
    c = fgetc( fp ); 
  } 
  fclose( fp ); 
 } 

Classification: ANSI 

Systems: All


### putenv

Synopsis: 
#include <process.h> 
int putenv( const char *env_name ); 

Description: The environment list consists of a number of environment names, each of which has a value associated with it.  Entries can be added to the environment list with the DOS set command or with the putenv function.  All entries in the environment list can be displayed by using the DOS set command with no arguments.  A program can obtain the value for an environment variable by using the  getenv function. 
When the value of env_name has the format 
    
     env_name=value 
an environment name and its value is added to the environment list.  When the value of env_name has the format 
    
     env_name= 
the environment name and value is removed from the environment list. 
The matching is case-insensitive; all lowercase letters are treated as if they were in upper case. 
The space into which environment names and their values are placed is limited.  Consequently, the putenv function can fail when there is insufficient space remaining to store an additional value. 
NOTE:  If the argument env_name is not a literal string, you should duplicate the string, since putenv does not copy the value; for example, 
    
     putenv( strdup( buffer ) ); 
To assign a string to a variable and place it in the environment list: 
    
     C>SET INCLUDE=C:\WATCOM\H 
To see what variables are in the environment list, and their current assignments: 
    
     C>SET 
     COMSPEC=C:\COMMAND.COM 
     PATH=C:\;C:\WATCOM 
     INCLUDE=C:\WATCOM\H 
     C> 

Returns: The putenv function returns zero when it is successfully executed and returns -1 when it fails. 

Errors: When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

ENOMEM Not enough memory to allocate a new environment string. 

See Also: clearenv, getenv, setenv 

Example: 
The following gets the string currently assigned to  INCLUDE and displays it, assigns a new value to it, gets and displays it, and then removes the environment name and value. 
#include <stdio.h> 
#include <stdlib.h> 
void main() 
 { 
  char *path; 
  path = getenv( "INCLUDE" ); 
  if( path != NULL ) 
    printf( "INCLUDE=%s\n", path ); 
  if( putenv( "INCLUDE=mylib;yourlib" ) != 0 ) 
    printf( "putenv failed" ); 
  path = getenv( "INCLUDE" ); 
  if( path != NULL ) 
    printf( "INCLUDE=%s\n", path ); 
  if( putenv( "INCLUDE=" ) != 0 ) 
    printf( "putenv failed" ); 
 } 
produces the following: 
INCLUDE=C:\WATCOM\H 
INCLUDE=mylib;yourlib 

Classification: WATCOM 

Systems: All


### _putimage, _putimage_w

Synopsis: 
#include <graph.h> 
void _FAR _putimage( short x, short y, 
           char _HUGE *image, short mode ); 
void _FAR _putimage_w( double x, double y, 
            char _HUGE *image, short mode ); 

Description: The _putimage functions display the screen image indicated by the argument image.  The _putimage function uses the view coordinate system.  The _putimage_w function uses the window coordinate system. 
The image is displayed upon the screen with its top left corner located at the point with coordinates (x,y).  The image was previously saved using the  _getimage functions.  The image is displayed in a rectangle whose size is the size of the rectangular image saved by the  _getimage functions. 
The image can be displayed in a number of ways, depending upon the value of the mode argument.  This argument can have the following values: 

_GPSET replace the rectangle on the screen by the saved image 

_GPRESET replace the rectangle on the screen with the pixel values of the saved image inverted; this produces a negative image 

_GAND produce a new image on the screen by ANDing together the pixel values from the screen with those from the saved image 

_GOR produce a new image on the screen by ORing together the pixel values from the screen with those from the saved image 

_GXOR produce a new image on the screen by exclusive ORing together the pixel values from the screen with those from the saved image; the original screen is restored by two successive calls to the _putimage function with this value, providing an efficient method to produce animated effects 

Returns: The _putimage functions do not return a value. 

See Also: _getimage, _imagesize 

Example: 
#include <conio.h> 
#include <graph.h> 
#include <malloc.h> 
main() 
{ 
  char *buf; 
  int y; 
  _setvideomode( _VRES16COLOR ); 
  _ellipse( _GFILLINTERIOR, 100, 100, 200, 200 ); 
  buf = malloc( _imagesize( 100, 100, 201, 201 ) ); 
  if( buf != NULL ) { 
    _getimage( 100, 100, 201, 201, buf ); 
    _putimage( 260, 200, buf, _GPSET ); 
    _putimage( 420, 100, buf, _GPSET ); 
    for( y = 100; y < 300; ) { 
      _putimage( 420, y, buf, _GXOR ); 
      y += 20; 
      _putimage( 420, y, buf, _GXOR ); 
    } 
    free( buf ); 
  } 
  getch(); 
  _setvideomode( _DEFAULTMODE ); 
} 

Classification: PC Graphics 

Systems:  _putimage - DOS, QNX 
_putimage_w - DOS, QNX


### puts

Synopsis: 
#include <stdio.h> 
int puts( const char *buf ); 

Description: The puts function writes the character string pointed to by buf to the output stream designated by  stdout, and appends a new-line character to the output.  The terminating null character is not written. 

Returns: The puts function returns a non-zero value if an error occurs; otherwise, it returns zero.  When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

See Also: fputs, putc 

Example: 
#include <stdio.h> 
void main() 
 { 
  FILE *fp; 
  char buffer[80]; 
  fp = freopen( "file", "r", stdin ); 
  while( gets( buffer ) != NULL ) { 
    puts( buffer ); 
  } 
  fclose( fp ); 
 } 

Classification: ANSI 

Systems: All


### qsort

Synopsis: 
#include <stdlib.h> 
void qsort( void *base, 
      size_t num, 
      size_t width, 
      int (*compar) 
         ( const void *, const void *) ); 

Description: The  qsort function sorts an array of num elements, which is pointed to by base, using Hoare's Quicksort algorithm.  Each element in the array is width bytes in size.  The comparison function pointed to by compar is called with two arguments that point to elements in the array.  The comparison function shall return an integer less than, equal to, or greater than zero if the first argument is less than, equal to, or greater than the second argument. 

Returns: The  qsort function returns no value. 

See Also: bsearch 

Example: 
#include <stdio.h> 
#include <stdlib.h> 
#include <string.h> 
char *CharVect[] = { "last", "middle", "first" }; 
int compare( const void *op1, const void *op2 ) 
 { 
  const char **p1 = (const char **) op1; 
  const char **p2 = (const char **) op2; 
  return( strcmp( *p1, *p2 ) ); 
 } 
void main() 
 { 
  qsort( CharVect, sizeof(CharVect)/sizeof(char *), 
     sizeof(char *), compare ); 
  printf( "%s %s %s\n", 
      CharVect[0], CharVect[1], CharVect[2] ); 
 } 
produces the following: 
first last middle 

Classification: ANSI 

Systems: All


### raise

Synopsis: 
int raise( int condition ); 
#include <signal.h> 

Description: The raise function signals the exceptional condition indicated by the condition argument.  The possible conditions are defined in the <signal.h> header file and are documented with the  signal function.  The  signal function can be used to specify the action which is to take place when such a condition occurs. 

Returns: The raise function returns zero when the condition is successfully raised and a non-zero value otherwise.  There may be no return of control following the function call if the action for that condition is to terminate the program or to transfer control using the  longjmp function. 

See Also: signal 

Example: 
/* 
 * This program loops until a SIGINT signal 
 * is received or a count is exceeded. 
 */ 
#include <stdio.h> 
#include <signal.h> 
sig_atomic_t signal_count; 
sig_atomic_t signal_number; 
static void alarm_handler( int signum ) 
 { 
  ++signal_count; 
  signal_number = signum; 
 } 
void main() 
 { 
  unsigned long i; 
  signal_count = 0; 
  signal_number = 0; 
  signal( SIGINT, alarm_handler ); 
  printf( "Program looping. Press Ctrl/C.\n" ); 
  for( i = 0; i < 3000000; i++ ) { 
   if( i > 2000000 ) raise( SIGINT ); 
   if( signal_count > 0 ) { 
    printf( "Signal %d received\n", signal_number ); 
    break; 
   } 
  } 
 } 

Classification: ANSI 

Systems: All


### rand

Synopsis: 
#include <stdlib.h> 
int rand( void ); 

Description: The rand function computes a sequence of pseudo-random integers in the range 0 to  RAND_MAX (32767).  The sequence can be started at different values by calling the  srand function. 

Returns: The  rand function returns a pseudo-random integer. 

See Also: srand 

Example: 
#include <stdio.h> 
#include <stdlib.h> 
void main() 
 { 
  int i; 
  for( i=1; i < 10; ++i ) { 
   printf( "%d\n", rand() ); 
  } 
 } 

Classification: ANSI 

Systems: All


### read

Synopsis: 
#include <io.h> 
int read( int handle, void *buffer, unsigned len ); 

Description: The read function reads data at the operating system level.  The number of bytes transmitted is given by len and the data is transmitted starting at the address specified by buffer. 
The handle value is returned by the  open function.  The access mode must have included either O_RDONLY or O_RDWR when the  open function was invoked.  The data is read starting at the current file position for the file in question.  This file position can be determined with the  tell function and can be set with the  lseek function. 
When O_BINARY is included in the access mode, the data is transmitted unchanged.  When O_TEXT is included in the access mode, the data is transmitted with the extra carriage return character removed before each linefeed character encountered in the original data. 

Returns: The read function returns the number of bytes of data transmitted from the file to the buffer (this does not include any carriage-return characters that were removed during the transmission).  Normally, this is the number given by the len argument.  When the end of the file is encountered before the read completes, the return value will be less than the number of bytes requested. 
A value of -1 is returned when an input/output error is detected.  When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

See Also: close, creat, fread, open, write 

Example: 
#include <stdio.h> 
#include <fcntl.h> 
#include <io.h> 
void main() 
 { 
  int  handle; 
  int  size_read; 
  char buffer[80]; 
  /* open a file for input        */ 
  handle = open( "file", O_RDONLY | O_TEXT ); 
  if( handle != -1 ) { 
   /* read the text            */ 
   size_read = read( handle, buffer, 
            sizeof( buffer ) ); 
   /* test for error           */ 
   if( size_read == -1 ) { 
     printf( "Error reading file\n" ); 
   } 
   /* close the file           */ 
   close( handle ); 
  } 
 } 

Classification: POSIX 1003.1 

Systems: All


### readdir

Synopsis: 
#include <direct.h> 
struct dirent *readdir( DIR *dirp ); 

Description: The readdir function obtains information about the next matching file name from the argument dirp.  The argument dirp is the value returned from the  opendir function.  The readdir function can be called repeatedly to obtain the list of file names contained in the directory specified by the pathname given to  opendir.  The function  closedir must be called to close the directory and free the memory allocated by  opendir. 
The file <direct.h> contains definitions for the structure  dirent. 
typedef struct dirent { 
  char   d_dta[ 21 ];    /* disk transfer area */ 
  char   d_attr;       /* file's attribute */ 
  unsigned short int d_time; /* file's time */ 
  unsigned short int d_date; /* file's date */ 
  long   d_size;       /* file's size */ 
  char   d_name[ 13 ];    /* file's name */ 
  ino_t  d_ino;       /* serial number */ 
  char   d_first;      /* flag for 1st time */ 
} DIR; 

Returns: When successful, readdir returns a pointer to an object of type struct dirent.  When an error occurs, readdir returns the value NULL and  errno is set to indicate the error.  When the end of the directory is encountered, readdir returns the value NULL and  errno is unchanged. 

Errors: When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

EBADF The argument dirp does not refer to an open directory stream. 

See Also: closedir, _dos_find Functions, opendir 

Example: 
To get a list of files contained in the directory \watcom\h on your default disk: 
#include <stdio.h> 
#include <direct.h> 
void main() 
 { 
  DIR *dirp; 
  struct dirent *direntp; 
  dirp = opendir( "\\watcom\\h" ); 
  if( dirp != NULL ) { 
   for(;;) { 
    direntp = readdir( dirp ); 
    if( direntp == NULL ) break; 
    printf( "%s\n", direntp->d_name ); 
   } 
   closedir( dirp ); 
  } 
 } 
Note the use of two adjacent backslash characters (\) within character-string constants to signify a single backslash. 

Classification: POSIX 1003.1 

Systems: All


### realloc Functions

Synopsis: 
#include <stdlib.h>  For ANSI compatibility (realloc only) 
#include <malloc.h>  Required for other function prototypes 
void * realloc( void *old_blk, size_t size ); 
void __based(void) *_brealloc( __segment seg, 
                void __based(void) *old_blk, 
                size_t size ); 
void __far  *_frealloc( void __far  *old_blk, 
               size_t size ); 
void __near *_nrealloc( void __near *old_blk, 
               size_t size ); 

Description: When the value of the old_blk argument is NULL, a new block of memory of size bytes is allocated. 
If the value of size is zero, the corresponding  free function is called to release the memory pointed to by old_blk. 
Otherwise, the  realloc function re-allocates space for an object of size bytes by either: 

oshrinking the allocated size of the allocated memory block old_blk when size is sufficiently smaller than the size of old_blk. 
oextending the allocated size of the allocated memory block old_blk if there is a large enough block of unallocated memory immediately following old_blk. 
oallocating a new block and copying the contents of old_blk to the new block. 
Because it is possible that a new block will be allocated, any pointers into the old memory should not be maintained.  old_blk.  These pointers will point to freed memory, with possible disastrous results, when a new block is allocated. 
The function returns NULL when the memory pointed to by old_blk cannot be re-allocated.  In this case, the memory pointed to by old_blk is not freed so care should be exercised to maintain a pointer to the old memory block. 
    
   buffer = (char *) realloc( buffer, 100 ); 
In the above example, buffer will be set to NULL if the function fails and will no longer point to the old memory block.  If buffer was your only pointer to the memory block then you will have lost access to this memory. 
Each function reallocates memory from a particular heap, as listed below: 

realloc Depends on data model of the program 

_brealloc Based heap specified by seg value 

_frealloc Far heap (outside the default data segment) 

_nrealloc Near heap (inside the default data segment) 
In a small data memory model, the  realloc function is equivalent to the  _nrealloc function; in a large data memory model, the  realloc function is equivalent to the  _frealloc function. 

Returns: The  realloc functions return a pointer to the start of the re-allocated memory.  The return value is NULL if there is insufficient memory available or if the value of the size argument is zero.  The  _brealloc function returns  _NULLOFF if there is insufficient memory available or if the requested size is zero. 

See Also: calloc Functions, _expand Functions, free Functions, halloc, hfree, malloc Functions, _msize Functions, sbrk 

Example: 
#include <stdlib.h> 
#include <malloc.h> 
void main() 
 { 
  char *buffer; 
  char *new_buffer; 
  buffer = (char *) malloc( 80 ); 
  new_buffer = (char *) realloc( buffer, 100 ); 
  if( new_buffer == NULL ) { 
   /* not able to allocate larger buffer */ 
  } else { 
   buffer = new_buffer; 
  } 
 } 

Classification: realloc is ANSI; _brealloc, _frealloc, and _nrealloc are not ANSI 

Systems:  realloc - All 
_brealloc - DOS/16, Win/16, QNX/16, OS/2 1.x(all) 
_frealloc - DOS/16, Win/16, QNX/16, OS/2 1.x(all) 
_nrealloc - DOS, Win, QNX, OS/2 1.x, OS/2 1.x(MT), OS/2 2.x, NT


### _rectangle, _rectangle_w, _rectangle_wxy

Synopsis: 
#include <graph.h> 
short _FAR _rectangle( short fill, 
            short x1, short y1, 
            short x2, short y2 ); 
short _FAR _rectangle_w( short fill, 
             double x1, double y1, 
             double x2, double y2 ); 
short _FAR _rectangle_wxy( short fill, 
              struct _wxycoord _FAR *p1, 
              struct _wxycoord _FAR *p2 ); 

Description: The _rectangle functions draw rectangles.  The _rectangle function uses the view coordinate system.  The _rectangle_w and _rectangle_wxy functions use the window coordinate system. 
The rectangle is defined with opposite corners established by the points (x1,y1) and (x2,y2). 
The argument fill determines whether the rectangle is filled in or has only its outline drawn.  The argument can have one of two values: 

_GFILLINTERIOR fill the interior by writing pixels with the current plot action using the current color and the current fill mask 

_GBORDER leave the interior unchanged; draw the outline of the figure with the current plot action using the current color and line style 

Returns: The _rectangle functions return a non-zero value when the rectangle was successfully drawn; otherwise, zero is returned. 

See Also: _setcolor, _setfillmask, _setlinestyle, _setplotaction 

Example: 
#include <conio.h> 
#include <graph.h> 
main() 
{ 
  _setvideomode( _VRES16COLOR ); 
  _rectangle( _GBORDER, 100, 100, 540, 380 ); 
  getch(); 
  _setvideomode( _DEFAULTMODE ); 
} 
produces the following: 
The graphical image cannot be reproduced here. See the printed 
version of the manual. 

Classification: PC Graphics 

Systems:  _rectangle - DOS, QNX 
_rectangle_w - DOS, QNX 
_rectangle_wxy - DOS, QNX


### _registerfonts

Synopsis: 
#include <graph.h> 
short _FAR _registerfonts( char _FAR *path ); 

Description: The _registerfonts function initializes the font graphics system.  Fonts must be registered, and a font selected, before text can be displayed with the  _outgtext function. 
The argument path specifies the location of the font files.  This argument is a file specification, and can contain drive and directory components and may contain wildcard characters.  The _registerfonts function opens each of the font files specified and reads the font information.  Memory is allocated to store the characteristics of the font.  These font characteristics are used by the  _setfont function when selecting a font. 

Returns: The _registerfonts function returns the number of fonts that were registered if the function is successful; otherwise, a negative number is returned. 

See Also: _unregisterfonts, _setfont, _getfontinfo, _outgtext, _getgtextextent, _setgtextvector, _getgtextvector 

Example: 
#include <conio.h> 
#include <stdio.h> 
#include <graph.h> 
main() 
{ 
  int i, n; 
  char buf[ 10 ]; 
  _setvideomode( _VRES16COLOR ); 
  n = _registerfonts( "*.fon" ); 
  for( i = 0; i < n; ++i ) { 
    sprintf( buf, "n%d", i ); 
    _setfont( buf ); 
    _moveto( 100, 100 ); 
    _outgtext( "WATCOM Graphics" ); 
    getch(); 
    _clearscreen( _GCLEARSCREEN ); 
  } 
  _unregisterfonts(); 
  _setvideomode( _DEFAULTMODE ); 
} 

Classification: PC Graphics 

Systems: DOS, QNX


### _remapallpalette

Synopsis: 
#include <graph.h> 
short _FAR _remapallpalette( long _FAR *colors ); 

Description: The _remapallpalette function sets (or remaps) all of the colors in the palette.  The color values in the palette are replaced by the array of color values given by the argument colors.  This function is supported in all video modes, but only works with EGA, MCGA and VGA adapters. 
The array colors must contain at least as many elements as there are supported colors.  The newly mapped palette will cause the complete screen to change color wherever there is a pixel value of a changed color in the palette. 
The representation of colors depends upon the hardware being used.  The number of colors in the palette can be determined by using the  _getvideoconfig function. 

Returns: The _remapallpalette function returns (-1) if the palette is remapped successfully and zero otherwise. 

See Also: _remappalette, _getvideoconfig 

Example: 
#include <conio.h> 
#include <graph.h> 
long colors[ 16 ] = { 
  _BRIGHTWHITE, _YELLOW, _LIGHTMAGENTA, _LIGHTRED, 
  _LIGHTCYAN, _LIGHTGREEN, _LIGHTBLUE, _GRAY, _WHITE, 
  _BROWN, _MAGENTA, _RED, _CYAN, _GREEN, _BLUE, _BLACK, 
}; 
main() 
{ 
  int x, y; 
  _setvideomode( _VRES16COLOR ); 
  for( y = 0; y < 4; ++y ) { 
    for( x = 0; x < 4; ++x ) { 
      _setcolor( x + 4 * y ); 
      _rectangle( _GFILLINTERIOR, 
          x * 160, y * 120, 
          ( x + 1 ) * 160, ( y + 1 ) * 120 ); 
    } 
  } 
  getch(); 
  _remapallpalette( &colors ); 
  getch(); 
  _setvideomode( _DEFAULTMODE ); 
} 

Classification: PC Graphics 

Systems: DOS, QNX


### _remappalette

Synopsis: 
#include <graph.h> 
long _FAR _remappalette( short pixval, long color ); 

Description: The _remappalette function sets (or remaps) the palette color pixval to be the color color.  This function is supported in all video modes, but only works with EGA, MCGA and VGA adapters. 
The argument pixval is an index in the color palette of the current video mode.  The argument color specifies the actual color displayed on the screen by pixels with pixel value pixval.  Color values are selected by specifying the red, green and blue intensities that make up the color.  Each intensity can be in the range from 0 to 63, resulting in 262144 possible different colors.  A given color value can be conveniently specified as a value of type long.  The color value is of the form 0x00bbggrr, where bb is the blue intensity, gg is the green intensity and rr is the red intensity of the selected color.  The file graph.h defines constants containing the color intensities of each of the 16 default colors. 
The _remappalette function takes effect immediately.  All pixels on the complete screen which have a pixel value equal to the value of pixval will now have the color indicated by the argument color. 

Returns: The _remappalette function returns the previous color for the pixel value if the palette is remapped successfully; otherwise, (-1) is returned. 

See Also: _remapallpalette, _setvideomode 

Example: 
#include <conio.h> 
#include <graph.h> 
long colors[ 16 ] = { 
  _BLACK, _BLUE, _GREEN, _CYAN, 
  _RED, _MAGENTA, _BROWN, _WHITE, 
  _GRAY, _LIGHTBLUE, _LIGHTGREEN, _LIGHTCYAN, 
  _LIGHTRED, _LIGHTMAGENTA, _YELLOW, _BRIGHTWHITE 
}; 
main() 
{ 
  int col; 
  _setvideomode( _VRES16COLOR ); 
  for( col = 0; col < 16; ++col ) { 
    _remappalette( 0, colors[ col ] ); 
    getch(); 
  } 
  _setvideomode( _DEFAULTMODE ); 
} 

Classification: PC Graphics 

Systems: DOS, QNX


### remove

Synopsis: 
#include <stdio.h> 
int remove( const char *filename ); 

Description: The  remove function deletes the file whose name is the string pointed to by filename. 

Returns: The  remove function returns zero if the operation succeeds, non-zero if it fails.  When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

Example: 
#include <stdio.h> 
void main() 
 { 
  remove( "vm.tmp" ); 
 } 

Classification: ANSI 

Systems: All


### rename

Synopsis: 
#include <stdio.h> 
int rename( const char *old, const char *new ); 

Description: The rename function causes the file whose name is indicated by the string old to be renamed to the name given by the string new. 

Returns: The rename function returns zero if the operation succeeds, a non-zero value if it fails.  When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

Example: 
#include <stdio.h> 
void main() 
 { 
  rename( "old.dat", "new.dat" ); 
 } 

Classification: ANSI 

Systems: All


### rewind

Synopsis: 
#include <stdio.h> 
void rewind( FILE *fp ); 

Description: The rewind function sets the file position indicator for the stream indicated to by fp to the beginning of the file.  It is equivalent to 
    
     fseek( fp, 0L, SEEK_SET ); 
except that the error indicator for the stream is cleared. 

Returns: The  rewind function returns no value. 

See Also: fopen, clearerr 

Example: 
#include <stdio.h> 
static assemble_pass( int passno ) 
 { 
  printf( "Pass %d\n", passno ); 
 } 
void main() 
 { 
  FILE *fp; 
  if( (fp = fopen( "program.asm", "r")) != NULL ) { 
    assemble_pass( 1 ); 
    rewind( fp ); 
    assemble_pass( 2 ); 
    fclose( fp ); 
  } 
 } 

Classification: ANSI 

Systems: All


### rmdir

Synopsis: 
#include <sys\types.h> 
#include <direct.h> 
int rmdir( const char *path ); 

Description: The rmdir function removes (deletes) the specified directory.  The directory must not contain any files or directories.  The path can be either relative to the current working directory or it can be an absolute path name. 

Returns: The rmdir function returns zero if successful and -1 otherwise. 

Errors: When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

See Also: chdir, chmod, getcwd, mkdir, stat 

Example: 
To remove the directory called \watcom on drive C: 
#include <sys\types.h> 
#include <direct.h> 
void main() 
 { 
  rmdir( "c:\\watcom" ); 
 } 
Note the use of two adjacent backslash characters (\) within character-string constants to signify a single backslash. 

Classification: POSIX 1003.1 

Systems: All


### _rotl

Synopsis: 
#include <stdlib.h> 
unsigned int _rotl( unsigned int value, 
          unsigned int shift ); 

Description: The _rotl function rotates the unsigned integer, determined by value, to the left by the number of bits specified in shift.  If you port an application using _rotl between a 16-bit and a 32-bit environment, you will get different results because of the difference in the size of integers. 

Returns: The rotated value is returned. 

See Also: _lrotl, _lrotr, _rotr 

Example: 
#include <stdio.h> 
#include <stdlib.h> 
unsigned int mask = 0x0F00; 
void main() 
 { 
  mask = _rotl( mask, 4 ); 
  printf( "%04X\n", mask ); 
 } 
produces the following: 
F000 

Classification: WATCOM 

Systems: All


### _rotr

Synopsis: 
#include <stdlib.h> 
unsigned int _rotr( unsigned int value, 
          unsigned int shift ); 

Description: The _rotr function rotates the unsigned integer, determined by value, to the right by the number of bits specified in shift.  If you port an application using _rotr between a 16-bit and a 32-bit environment, you will get different results because of the difference in the size of integers. 

Returns: The rotated value is returned. 

See Also: _lrotl, _lrotr, _rotl 

Example: 
#include <stdio.h> 
#include <stdlib.h> 
unsigned int mask = 0x1230; 
void main() 
 { 
  mask = _rotr( mask, 4 ); 
  printf( "%04X\n", mask ); 
 } 
produces the following: 
0123 

Classification: WATCOM 

Systems: All


### sbrk

Synopsis: 
#include <stdlib.h> 
void *sbrk( int increment ); 

Description: The sbrk sets the "break" value for the program by adding the value of increment to the current break value.  This increment may be positive or negative. 
The "break" value is the address of the first byte of unallocated memory.  When a program starts execution, the break value is placed following the code and constant data for the program.  As memory is allocated, this pointer will advance when there is no freed block large enough to satisfy an allocation request. 
A new process started with one of the  spawn...  or  exec...  functions is loaded following the break value.  Consequently, decreasing the break value leaves more space available to the new process.  Similarly, for a resident program (a program which remains in memory while another program executes), increasing the break value will leave more space available to be allocated by the resident program after other programs are loaded. 

Returns: The function returns the old break value when the break value has been reset; otherwise, -1 is returned.  When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

See Also: calloc Functions, _expand Functions, free Functions, halloc, hfree, malloc Functions, _msize Functions, realloc Functions 

Example: 
#include <stdio.h> 
#include <stdlib.h> 
void main() 
 { 
  void *brk; 
  brk = sbrk( 0x0000 ); 
  printf( "Old break value %p\n", brk ); 
  brk = sbrk( -0x0100 ); 
  printf( "Old break value %p\n", brk ); 
  brk = sbrk( 0x0000 ); 
  printf( "New break value %p\n", brk ); 
 } 

Classification: WATCOM 

Systems: DOS, Win, QNX, OS/2 1.x, OS/2 1.x(MT), OS/2 2.x, NT


### scanf

Synopsis: 
#include <stdio.h> 
int scanf( const char *format, ... ); 

Description: The scanf function scans input from the file designated by  stdin under control of the argument format.  The format string is described below.  Following the format string is the list of addresses of items to receive values. 

Returns: The scanf function returns  EOF when the scanning is terminated by reaching the end of the input stream.  Otherwise, the number of input arguments for which values were successfully scanned and stored is returned. 

See Also: cscanf, fscanf, sscanf, vcscanf, vfscanf, vscanf, vsscanf 

Example: 
To scan a date in the form "Saturday April 18 1987": 
#include <stdio.h> 
void main() 
 { 
  int day, year; 
  char weekday[10], month[12]; 
  scanf( "%s %s %d %d", weekday, month, &day, &year ); 
 } 

Format Control String: The format control string consists of zero or more format directives that specify acceptable input file data.  Subsequent arguments are pointers to various types of objects that are assigned values as the format string is processed. 
A format directive can be a sequence of one or more white-space characters, an ordinary character, or a conversion specifier.  An ordinary character in the format string is any character, other than a white-space character or the percent character (%), that is not part of a conversion specifier.  A conversion specifier is a sequence of characters in the format string that begins with a percent character (%) and is followed, in sequence, by the following: 

oan optional assignment suppression indicator:  the asterisk character (*) 
oan optional decimal integer that specifies the maximum field width to be scanned for the conversion 
oan optional pointer-type specification:  one of "N" or "F" 
oan optional type length specification:  one of "h", "l" or "L" 
oa character that specifies the type of conversion to be performed:  one of the characters cdefgionpsux[ 
As each format directive in the format string is processed, the directive may successfully complete, fail because of a lack of input data, or fail because of a matching error as defined by the particular directive.  If end-of-file is encountered on the input data before any characters that match the current directive have been processed (other than leading white-space where permitted), the directive fails for lack of data.  If end-of-file occurs after a matching character has been processed, the directive is completed (unless a matching error occurs), and the function returns without processing the next directive.  If a directive fails because of an input character mismatch, the character is left unread in the input stream.  Trailing white-space characters, including new-line characters, are not read unless matched by a directive.  When a format directive fails, or the end of the format string is encountered, the scanning is completed and the function returns. 
When one or more white-space characters (space " ", horizontal tab "\t", vertical tab "\v", form feed "\f", carriage return "\r", new line or linefeed "\n") occur in the format string, input data up to the first non-white-space character is read, or until no more data remains.  If no white-space characters are found in the input data, the scanning is complete and the function returns. 
An ordinary character in the format string is expected to match the same character in the input stream. 
A conversion specifier in the format string is processed as follows: 

ofor conversion types other than "[", "c" and "n", leading white-space characters are skipped 
ofor conversion types other than "n", all input characters, up to any specified maximum field length, that can be matched by the conversion type are read and converted to the appropriate type of value; the character immediately following the last character to be matched is left unread; if no characters are matched, the format directive fails 
ounless the assignment suppression indicator ("*") was specified, the result of the conversion is assigned to the object pointed to by the next unused argument (if assignment suppression was specified, no argument is skipped); the arguments must correspond in number, type and order to the conversion specifiers in the format string 
A pointer-type specification is used to indicate the type of pointer used to locate the next argument to be scanned: 

F pointer is a far pointer 

N pointer is a near pointer 
The pointer type defaults to that used for data in the memory model for which the program has been compiled. 
A type length specifier affects the conversion as follows: 

o"h" causes a "d", "i", "o", "u" or "x" (integer) conversion to assign the converted value to an object of type short int or unsigned short int 
o"h" causes an "f" conversion to assign a fixed-point number to an object of type long consisting of a 16-bit integer part and a 16-bit fractional part. 
o"h" causes an "n" (read length assignment) operation to assign the number of characters that have been read to an object of type unsigned short int 
o"l" causes a "d", "i", "o", "u" or "x" (integer) conversion to assign the converted value to an object of type long int or unsigned long int 
o"l" causes an "n" (read length assignment) operation to assign the number of characters that have been read to an object of type unsigned long int 
o"l" causes an "e", "f" or "g" (floating-point) conversion to assign the converted value to an object of type double 
o"L" causes an "e", "f" or "g" (floating-point) conversion to assign the converted value to an object of type long double 
The valid conversion type specifiers are: 

c Any sequence of characters in the input stream of the length specified by the field width, or a single character if no field width is specified, is matched.  The argument is assumed to point to the first element of a character array of sufficient size to contain the sequence, without a terminating null character ('\0').  For a single character assignment, a pointer to a single object of type char is sufficient. 

d A decimal integer, consisting of an optional sign, followed by one or more decimal digits, is matched.  The argument is assumed to point to an object of type int. 

e, f, g A floating-point number, consisting of an optional sign ("+" or "-"), followed by one or more decimal digits, optionally containing a decimal-point character, followed by an optional exponent of the form "e" or "E", an optional sign and one or more decimal digits, is matched.  The exponent, if present, specifies the power of ten by which the decimal fraction is multiplied.  The argument is assumed to point to an object of type float. 

i An optional sign, followed by an octal, decimal or hexadecimal constant is matched.  An octal constant consists of "0" and zero or more octal digits.  A decimal constant consists of a non-zero decimal digit and zero or more decimal digits.  A hexadecimal constant consists of the characters "0x" or "0X" followed by one or more (upper- or lowercase) hexadecimal digits.  The argument is assumed to point to an object of type int. 

n No input data is processed.  Instead, the number of characters that have already been read is assigned to the object of type unsigned int that is pointed to by the argument.  The number of items that have been scanned and assigned (the return value) is not affected by the "n" conversion type specifier. 

o An octal integer, consisting of an optional sign, followed by one or more (zero or non-zero) octal digits, is matched.  The argument is assumed to point to an object of type int. 

p A hexadecimal integer, as described for "x" conversions below, is matched.  The converted value is further converted to a value of type void* and then assigned to the object pointed to by the argument. 

s A sequence of non-white-space characters is matched.  The argument is assumed to point to the first element of a character array of sufficient size to contain the sequence and a terminating null character, which is added by the conversion operation. 

u An unsigned decimal integer, consisting of one or more decimal digits, is matched.  The argument is assumed to point to an object of type unsigned int. 

x A hexadecimal integer, consisting of an optional sign, followed by an optional prefix "0x" or "0X", followed by one or more (upper- or lowercase) hexadecimal digits, is matched.  The argument is assumed to point to an object of type int. 

[c1c2...] A sequence of characters, consisting of any of the characters c1, c2, ...  called the scanset, in any order, is matched.  c1 cannot be the caret character ('^').  If c1 is "]", that character is considered to be part of the scanset and a second "]" is required to end the format directive.  The argument is assumed to point to the first element of a character array of sufficient size to contain the sequence and a terminating null character, which is added by the conversion operation. 

[^c1c2...] A sequence of characters, consisting of any of the characters other than the characters between the "^" and "]", is matched.  As with the preceding conversion, if c1 is "]", it is considered to be part of the scanset and a second "]" ends the format directive.  The argument is assumed to point to the first element of a character array of sufficient size to contain the sequence and a terminating null character, which is added by the conversion operation. 
A conversion type specifier of "%" is treated as a single ordinary character that matches a single "%" character in the input data.  A conversion type specifier other than those listed above causes scanning to terminate the function to return. 
The line 
scanf( "%s%*f%3hx%d", name, &hexnum, &decnum ) 
with input 
some_string 34.555e-3 abc1234 
will copy "some_string" into the array name, skip 34.555e-3, assign 0xabc to hexnum and 1234 to decnum.  The return value will be 3. 
The program 
#include < stdio.h> 
void main() 
 { 
  char string1[80], string2[80]; 
  scanf( "%[abcdefghijklmnopqrstuvwxyz" 
      "ABCDEFGHIJKLMNOPQRSTUVWZ ]%*2s%[^\n]", 
      string1, string2 ); 
  printf( "%s\n%s\n", string1, string2 ); 
 } 
with input 
They may look alike, but they don't perform alike. 
will assign 
"They may look alike" 
to string1, skip the comma (the "%*2s" will match only the comma; the following blank terminates that field), and assign 
" but they don't perform alike." 
to string2. 

Classification: ANSI, (except for F and N modifiers) 

Systems: All


### _scrolltextwindow

Synopsis: 
#include <graph.h> 
void _FAR _scrolltextwindow( short rows ); 

Description: The _scrolltextwindow function scrolls the lines in the current text window.  A text window is defined with the  _settextwindow function.  By default, the text window is the entire screen. 
The argument rows specifies the number of rows to scroll.  A positive value means to scroll the text window up or towards the top of the screen.  A negative value means to scroll the text window down or towards the bottom of the screen.  Specifying a number of rows greater than the height of the text window is equivalent to clearing the text window with the  _clearscreen function. 
Two constants are defined that can be used with the _scrolltextwindow function: 

_GSCROLLUP the contents of the text window are scrolled up (towards the top of the screen) by one row 

_GSCROLLDOWN the contents of the text window are scrolled down (towards the bottom of the screen) by one row 

Returns: The _scrolltextwindow function does not return a value. 

See Also: _settextwindow, _clearscreen, _outtext, _outmem, _settextposition 

Example: 
#include <conio.h> 
#include <graph.h> 
#include <stdio.h> 
main() 
{ 
  int i; 
  char buf[ 80 ]; 
  _setvideomode( _TEXTC80 ); 
  _settextwindow( 5, 20, 20, 40 ); 
  for( i = 1; i <= 10; ++i ) { 
    sprintf( buf, "Line %d\n", i ); 
    _outtext( buf ); 
  } 
  getch(); 
  _scrolltextwindow( _GSCROLLDOWN ); 
  getch(); 
  _scrolltextwindow( _GSCROLLUP ); 
  getch(); 
  _setvideomode( _DEFAULTMODE ); 
} 

Classification: PC Graphics 

Systems: DOS, QNX


### _searchenv

Synopsis: 
#include <stdlib.h> 
void _searchenv( const char *name, 
         const char *env_var, 
         char *buffer ); 

Description: The _searchenv function searches for the file specified by name in the list of directories assigned to the environment variable specified by env_var. Common values for env_var are PATH, LIB and INCLUDE. 
The current directory is searched first to find the specified file.  If the file is not found in the current directory, each of the directories specified by the environment variable is searched. 
The full pathname is placed in the buffer pointed to by the argument buffer.  If the specified file cannot be found, then buffer will contain an empty string. 

Returns: The _searchenv function returns no value. 

See Also: getenv, setenv, _splitpath, putenv 

Example: 
#include <stdio.h> 
#include <stdlib.h> 
void display_help( FILE *fp ) 
 { 
  printf( "display_help T.B.I.\n" ); 
 } 
void main() 
 { 
  FILE *help_file; 
  char full_path[ _MAX_PATH ]; 
  _searchenv( "watcomc.hlp", "PATH", full_path ); 
  if( full_path[0] == '\0' ) { 
   printf( "Unable to find help file\n" ); 
  } else { 
   help_file = fopen( full_path, "r" ); 
   display_help( help_file ); 
   fclose( help_file ); 
  } 
 } 

Classification: WATCOM 

Systems: All


### segread

Synopsis: 
#include <i86.h> 
void segread( struct SREGS *seg_regs ); 

Description: The segread function places the values of the segment registers into the structure located by seg_regs. 

Returns: No value is returned. 

See Also: FP_OFF, FP_SEG, MK_FP 

Example: 
#include <stdio.h> 
#include <i86.h> 
void main() 
 { 
  struct SREGS sregs; 
  segread( &sregs ); 
  printf( "Current value of CS is %04X\n", sregs.cs ); 
 } 

Classification: WATCOM 

Systems: All


### _selectpalette

Synopsis: 
#include <graph.h> 
short _FAR _selectpalette( short palnum ); 

Description: The _selectpalette function selects the palette indicated by the argument palnum from the color palettes available.  This function is only supported by the video modes _MRES4COLOR and _MRESNOCOLOR. 
Mode _MRES4COLOR supports four palettes of four colors.  In each palette, color 0, the background color, can be any of the 16 possible colors.  The color values associated with the other three pixel values, (1, 2 and 3), are determined by the selected palette. 
The following table outlines the available color palettes: 
    
   Palette        Pixel Values 
   Number   1        2        3 
    0   green      red       brown 
    1   cyan       magenta     white 
    2   light green   light red    yellow 
    3   light cyan    light magenta  bright white 

Returns: The _selectpalette function returns the number of the previously selected palette. 

See Also: _setvideomode, _getvideoconfig 

Example: 
#include <conio.h> 
#include <graph.h> 
main() 
{ 
  int x, y, pal; 
  _setvideomode( _MRES4COLOR ); 
  for( y = 0; y < 2; ++y ) { 
    for( x = 0; x < 2; ++x ) { 
      _setcolor( x + 2 * y ); 
      _rectangle( _GFILLINTERIOR, 
          x * 160, y * 100, 
          ( x + 1 ) * 160, ( y + 1 ) * 100 ); 
    } 
  } 
  for( pal = 0; pal < 4; ++pal ) { 
    _selectpalette( pal ); 
    getch(); 
  } 
  _setvideomode( _DEFAULTMODE ); 
} 

Classification: PC Graphics 

Systems: DOS, QNX


### _setactivepage

Synopsis: 
#include <graph.h> 
short _FAR _setactivepage( short pagenum ); 

Description: The _setactivepage function selects the page (in memory) to which graphics output is written.  The page to be selected is given by the pagenum argument. 
Only some combinations of video modes and hardware allow multiple pages of graphics to exist.  When multiple pages are supported, the active page may differ from the visual page.  The graphics information in the visual page determines what is displayed upon the screen.  Animation may be accomplished by alternating the visual page.  A graphics page can be constructed without affecting the screen by setting the active page to be different than the visual page. 
The number of available video pages can be determined by using the  _getvideoconfig function.  The default video page is 0. 

Returns: The _setactivepage function returns the number of the previous page when the active page is set successfully; otherwise, a negative number is returned. 

See Also: _getactivepage, _setvisualpage, _getvisualpage, _getvideoconfig 

Example: 
#include <conio.h> 
#include <graph.h> 
main() 
{ 
  int old_apage; 
  int old_vpage; 
  _setvideomode( _HRES16COLOR ); 
  old_apage = _getactivepage(); 
  old_vpage = _getvisualpage(); 
  /* draw an ellipse on page 0 */ 
  _setactivepage( 0 ); 
  _setvisualpage( 0 ); 
  _ellipse( _GFILLINTERIOR, 100, 50, 540, 150 ); 
  /* draw a rectangle on page 1 */ 
  _setactivepage( 1 ); 
  _rectangle( _GFILLINTERIOR, 100, 50, 540, 150 ); 
  getch(); 
  /* display page 1 */ 
  _setvisualpage( 1 ); 
  getch(); 
  _setactivepage( old_apage ); 
  _setvisualpage( old_vpage ); 
  _setvideomode( _DEFAULTMODE ); 
} 

Classification: PC Graphics 

Systems: DOS, QNX


### _setbkcolor

Synopsis: 
#include <graph.h> 
long _FAR _setbkcolor( long color ); 

Description: The _setbkcolor function sets the current background color to be that of the color argument.  In text modes, the background color controls the area behind each individual character.  In graphics modes, the background refers to the entire screen.  The default background color is 0. 
When the current video mode is a graphics mode, any pixels with a zero pixel value will change to the color of the color argument.  When the current video mode is a text mode, nothing will immediately change; only subsequent output is affected. 

Returns: The _setbkcolor function returns the previous background color. 

See Also: _getbkcolor 

Example: 
#include <conio.h> 
#include <graph.h> 
long colors[ 16 ] = { 
  _BLACK, _BLUE, _GREEN, _CYAN, 
  _RED, _MAGENTA, _BROWN, _WHITE, 
  _GRAY, _LIGHTBLUE, _LIGHTGREEN, _LIGHTCYAN, 
  _LIGHTRED, _LIGHTMAGENTA, _YELLOW, _BRIGHTWHITE 
}; 
main() 
{ 
  long old_bk; 
  int bk; 
  _setvideomode( _VRES16COLOR ); 
  old_bk = _getbkcolor(); 
  for( bk = 0; bk < 16; ++bk ) { 
    _setbkcolor( colors[ bk ] ); 
    getch(); 
  } 
  _setbkcolor( old_bk ); 
  _setvideomode( _DEFAULTMODE ); 
} 

Classification: PC Graphics 

Systems: DOS, QNX


### setbuf

Synopsis: 
#include <stdio.h> 
void setbuf( FILE *fp, char *buffer ); 

Description: The  setbuf function can be used to associate a buffer with the file designated by fp.  If this function is used, it must be called after the file has been opened and before it has been read or written.  If the argument buffer is NULL, then all input/output for the file fp will be completely unbuffered.  If the argument buffer is not NULL, then it must point to an array that is at least  BUFSIZ characters in length, and all input/output will be fully buffered. 

Returns: The  setbuf function returns no value. 

See Also: fopen, setvbuf 

Example: 
#include <stdio.h> 
#include <stdlib.h> 
void main() 
 { 
  char *buffer; 
  FILE *fp; 
  fp = fopen( "file", "r" ); 
  buffer = (char *) malloc( BUFSIZ ); 
  setbuf( fp, buffer ); 
  /* . */ 
  /* . */ 
  /* . */ 
  fclose( fp ); 
 } 

Classification: ANSI 

Systems: All


### _setcharsize, _setcharsize_w

Synopsis: 
#include <graph.h> 
void _FAR _setcharsize( short height, short width ); 
void _FAR _setcharsize_w( double height, double width ); 

Description: The _setcharsize functions set the character height and width to the values specified by the arguments height and width.  For the _setcharsize function, the arguments height and width represent a number of pixels.  For the _setcharsize_w function, the arguments height and width represent lengths along the y-axis and x-axis in the window coordinate system. 
These sizes are used when displaying text with the  _grtext function.  The default character sizes are dependent on the graphics mode selected, and can be determined by the  _gettextsettings function. 

Returns: The _setcharsize functions do not return a value. 

See Also: _grtext, _gettextsettings 

Example: 
#include <conio.h> 
#include <graph.h> 
main() 
{ 
  struct textsettings ts; 
  _setvideomode( _VRES16COLOR ); 
  _gettextsettings( &ts ); 
  _grtext( 100, 100, "WATCOM" ); 
  _setcharsize( 2 * ts.height, 2 * ts.width ); 
  _grtext( 100, 300, "Graphics" ); 
  _setcharsize( ts.height, ts.width ); 
  getch(); 
  _setvideomode( _DEFAULTMODE ); 
} 
produces the following: 
The graphical image cannot be reproduced here. See the printed 
version of the manual. 

Classification: PC Graphics 

Systems:  _setcharsize - DOS, QNX 
_setcharsize_w - DOS, QNX


### _setcharspacing, _setcharspacing_w

Synopsis: 
#include <graph.h> 
void _FAR _setcharspacing( short space ); 
void _FAR _setcharspacing_w( double space ); 

Description: The _setcharspacing functions set the current character spacing to have the value of the argument space.  For the _setcharspacing function, space represents a number of pixels.  For the _setcharspacing_w function, space represents a length along the x-axis in the window coordinate system. 
The character spacing specifies the additional space to leave between characters when a text string is displayed with the  _grtext function.  A negative value can be specified to cause the characters to be drawn closer together.  The default value of the character spacing is 0. 

Returns: The _setcharspacing functions do not return a value. 

See Also: _grtext, _gettextsettings 

Example: 
#include <conio.h> 
#include <graph.h> 
main() 
{ 
  _setvideomode( _VRES16COLOR ); 
  _grtext( 100, 100, "WATCOM" ); 
  _setcharspacing( 20 ); 
  _grtext( 100, 300, "Graphics" ); 
  getch(); 
  _setvideomode( _DEFAULTMODE ); 
} 
produces the following: 
The graphical image cannot be reproduced here. See the printed 
version of the manual. 

Classification: PC Graphics 

Systems:  _setcharspacing - DOS, QNX 
_setcharspacing_w - DOS, QNX


### _setcliprgn

Synopsis: 
#include <graph.h> 
void _FAR _setcliprgn( short x1, short y1, 
            short x2, short y2 ); 

Description: The _setcliprgn function restricts the display of graphics output to the clipping region.  This region is a rectangle whose opposite corners are established by the physical points (x1,y1) and (x2,y2). 
The _setcliprgn function does not affect text output using the  _outtext and  _outmem functions.  To control the location of text output, see the  _settextwindow function. 

Returns: The _setcliprgn function does not return a value. 

See Also: _settextwindow, _setvieworg, _setviewport 

Example: 
#include <conio.h> 
#include <graph.h> 
main() 
{ 
  short x1, y1, x2, y2; 
  _setvideomode( _VRES16COLOR ); 
  _getcliprgn( &x1, &y1, &x2, &y2 ); 
  _setcliprgn( 130, 100, 510, 380 ); 
  _ellipse( _GBORDER, 120, 90, 520, 390 ); 
  getch(); 
  _setcliprgn( x1, y1, x2, y2 ); 
  _setvideomode( _DEFAULTMODE ); 
} 

Classification: PC Graphics 

Systems: DOS, QNX


### _setcolor

Synopsis: 
#include <graph.h> 
short _FAR _setcolor( short pixval ); 

Description: The _setcolor function sets the pixel value for the current color to be that indicated by the pixval argument.  The current color is only used by the functions that produce graphics output; text output with  _outtext uses the current text color (see the  _settextcolor function).  The default color value is one less than the maximum number of colors in the current video mode. 

Returns: The _setcolor function returns the previous value of the current color. 

See Also: _getcolor, _settextcolor 

Example: 
#include <conio.h> 
#include <graph.h> 
main() 
{ 
  int col, old_col; 
  _setvideomode( _VRES16COLOR ); 
  old_col = _getcolor(); 
  for( col = 0; col < 16; ++col ) { 
    _setcolor( col ); 
    _rectangle( _GFILLINTERIOR, 100, 100, 540, 380 ); 
    getch(); 
  } 
  _setcolor( old_col ); 
  _setvideomode( _DEFAULTMODE ); 
} 

Classification: PC Graphics 

Systems: DOS, QNX


### setenv

Synopsis: 
#include <env.h> 
int setenv( const char *name, 
      const char *newvalue, 
      int overwrite ); 

Description: The environment list consists of a number of environment names, each of which has a value associated with it.  Entries can be added to the environment list with the DOS set command or with the setenv function.  All entries in the environment list can be displayed by using the DOS set command with no arguments.  A program can obtain the value for an environment variable by using the  getenv function. 
The setenv function searches the environment list for an entry of the form name=value.  If no such string is present, setenv adds an entry of the form name=newvalue to the environment list.  Otherwise, if the overwrite argument is non-zero, setenv either will change the existing value to newvalue or will delete the string name=value and add the string name=newvalue. 
If the newvalue pointer is NULL, all strings of the form name=value in the environment list will be deleted. 
The value of the pointer  environ may change across a call to the setenv function. 
The setenv function will make copies of the strings associated with name and newvalue. 
The matching is case-insensitive; all lowercase letters are treated as if they were in upper case. 
Entries can also be added to the environment list with the DOS set command or with the  putenv or  setenv functions.  All entries in the environment list can be obtained by using the  getenv function. 
To assign a string to a variable and place it in the environment list: 
    
     C>SET INCLUDE=C:\WATCOM\H 
To see what variables are in the environment list, and their current assignments: 
    
     C>SET 
     COMSPEC=C:\COMMAND.COM 
     PATH=C:\;C:\WATCOM 
     INCLUDE=C:\WATCOM\H 
     C> 

Returns: The setenv function returns zero upon successful completion.  Otherwise, it will return a non-zero value and set  errno to indicate the error. 

Errors: When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

ENOMEM Not enough memory to allocate a new environment string. 

See Also: clearenv, exec Functions, getenv, putenv, _searchenv, spawn Functions, system 

Example: 
The following will change the string assigned to  INCLUDE and then display the new string. 
#include <stdio.h> 
#include <stdlib.h> 
#include <env.h> 
void main() 
 { 
  char *path; 
  if( setenv( "INCLUDE", "D:\WATCOM\H", 1 ) == 0 ) 
   if( (path = getenv( "INCLUDE" )) != NULL ) 
    printf( "INCLUDE=%s\n", path ); 
 } 

Classification: POSIX 1003.1 

Systems: All


### _setfillmask

Synopsis: 
#include <graph.h> 
void _FAR _setfillmask( char _FAR *mask ); 

Description: The _setfillmask function sets the current fill mask to the value of the argument mask.  When the value of the mask argument is NULL, there will be no fill mask set. 
The fill mask is an eight-byte array which is interpreted as a square pattern (8 by 8) of 64 bits.  Each bit in the mask corresponds to a pixel.  When a region is filled, each point in the region is mapped onto the fill mask.  When a bit from the mask is one, the pixel value of the corresponding point is set using the current plotting action with the current color; when the bit is zero, the pixel value of that point is not affected. 
When the fill mask is not set, a fill operation will set all points in the fill region to have a pixel value of the current color.  By default, no fill mask is set. 

Returns: The _setfillmask function does not return a value. 

See Also: _getfillmask, _ellipse, _floodfill, _rectangle, _polygon, _pie, _setcolor, _setplotaction 

Example: 
#include <conio.h> 
#include <graph.h> 
char old_mask[ 8 ]; 
char new_mask[ 8 ] = { 0x81, 0x42, 0x24, 0x18, 
            0x18, 0x24, 0x42, 0x81 }; 
main() 
{ 
  _setvideomode( _VRES16COLOR ); 
  _getfillmask( old_mask ); 
  _setfillmask( new_mask ); 
  _rectangle( _GFILLINTERIOR, 100, 100, 540, 380 ); 
  _setfillmask( old_mask ); 
  getch(); 
  _setvideomode( _DEFAULTMODE ); 
} 
produces the following: 
The graphical image cannot be reproduced here. See the printed 
version of the manual. 

Classification: PC Graphics 

Systems: DOS, QNX


### _setfont

Synopsis: 
#include <graph.h> 
short _FAR _setfont( char _FAR *opt ); 

Description: The _setfont function selects a font from the list of registered fonts (see the  _registerfonts function).  The font selected becomes the current font and is used whenever text is displayed with the  _outgtext function.  The function will fail if no fonts have been registered, or if a font cannot be found that matches the given characteristics. 
The argument opt is a string of characters specifying the characteristics of the desired font.  These characteristics determine which font is selected.  The options may be separated by blanks and are not case-sensitive.  Any number of options may be specified and in any order.  The available options are: 

hX character height X (in pixels) 

wX character width X (in pixels) 

f choose a fixed-width font 

p choose a proportional-width font 

r choose a raster (bit-mapped) font 

v choose a vector font 

b choose the font that best matches the options 

nX choose font number X (the number of fonts is returned by the  _registerfonts function) 

t'facename' choose a font with specified facename 
The facename option is specified as a "t" followed by a facename enclosed in single quotes.  The available facenames are: 

Courier fixed-width raster font with serifs 

Helv proportional-width raster font without serifs 

Tms Rmn proportional-width raster font with serifs 

Script proportional-width vector font that appears similar to hand-writing 

Modern proportional-width vector font without serifs 

Roman proportional-width vector font with serifs 
When "nX" is specified to select a particular font, the other options are ignored. 
If the best fit option ("b") is specified, _setfont will always be able to select a font.  The font chosen will be the one that best matches the options specified. The following precedence is given to the options when selecting a font: 

 1.Pixel height (higher precedence is given to heights less than the specified height) 

 2.Facename 

 3.Pixel width 

 4.Font type (fixed or proportional) 
When a pixel height or width does not match exactly and a vector font has been selected, the font will be stretched appropriately to match the given size. 

Returns: The _setfont function returns zero if successful; otherwise, (-1) is returned. 

See Also: _registerfonts, _unregisterfonts, _getfontinfo, _outgtext, _getgtextextent, _setgtextvector, _getgtextvector 

Example: 
#include <conio.h> 
#include <stdio.h> 
#include <graph.h> 
main() 
{ 
  int i, n; 
  char buf[ 10 ]; 
  _setvideomode( _VRES16COLOR ); 
  n = _registerfonts( "*.fon" ); 
  for( i = 0; i < n; ++i ) { 
    sprintf( buf, "n%d", i ); 
    _setfont( buf ); 
    _moveto( 100, 100 ); 
    _outgtext( "WATCOM Graphics" ); 
    getch(); 
    _clearscreen( _GCLEARSCREEN ); 
  } 
  _unregisterfonts(); 
  _setvideomode( _DEFAULTMODE ); 
} 

Classification: PC Graphics 

Systems: DOS, QNX


### _setgtextvector

Synopsis: 
#include <graph.h> 
struct xycoord _FAR _setgtextvector( short x, short y ); 

Description: The _setgtextvector function sets the orientation for text output used by the  _outgtext function to the vector specified by the arguments (x,y).  Each of the arguments can have a value of -1, 0 or 1, allowing for text to be displayed at any multiple of a 45-degree angle.  The default text orientation, for normal left-to-right text, is the vector (1,0). 

Returns: The _setgtextvector function returns, as an xycoord structure, the previous value of the text orientation vector. 

See Also: _registerfonts, _unregisterfonts, _setfont, _getfontinfo, _outgtext, _getgtextextent, _getgtextvector 

Example: 
#include <conio.h> 
#include <graph.h> 
main() 
{ 
  struct xycoord old_vec; 
  _setvideomode( _VRES16COLOR ); 
  old_vec = _getgtextvector(); 
  _setgtextvector( 0, -1 ); 
  _moveto( 100, 100 ); 
  _outgtext( "WATCOM Graphics" ); 
  _setgtextvector( old_vec.xcoord, old_vec.ycoord ); 
  getch(); 
  _setvideomode( _DEFAULTMODE ); 
} 

Classification: PC Graphics 

Systems: DOS, QNX


### setjmp

Synopsis: 
#include <setjmp.h> 
int setjmp( jmp_buf env ); 

Description: The setjmp function saves its calling environment in its  jmp_buf argument, for subsequent use by the  longjmp function. 
In some cases, error handling can be implemented by using setjmp to record the point to which a return will occur following an error.  When an error is detected in a called function, that function uses  longjmp to jump back to the recorded position.  The original function which called setjmp must still be active (it cannot have returned to the function which called it). 
Special care must be exercised to ensure that any side effects that are left undone (allocated memory, opened files, etc.) are satisfactorily handled. 

Returns: The setjmp function returns zero when it is initially called.  The return value will be non-zero if the return is the result of a call to the  longjmp function.  An if statement is often used to handle these two returns.  When the return value is zero, the initial call to setjmp has been made; when the return value is non-zero, a return from a  longjmp has just occurred. 

See Also: longjmp 

Example: 
/* show LONGJMP, SETJMP */ 
#include <stdio.h> 
#include <setjmp.h> 
jmp_buf env; 
void main() 
 { 
  int ret_val; 
  ret_val = 293; 
  if( 0 == ( ret_val = setjmp( env ) ) ) { 
   printf( "after setjmp %d\n", ret_val ); 
   rtn(); 
   printf( "back from rtn %d\n", ret_val ); 
  } else { 
   printf( "back from longjmp %d\n", ret_val ); 
  } 
 } 
rtn() 
 { 
  printf( "about to longjmp\n" ); 
  longjmp( env, 14 ); 
 } 
produces the following: 
after setjmp 0 
about to longjmp 
back from longjmp 14 

Classification: ANSI 

Systems: MACRO


### _setlinestyle

Synopsis: 
#include <graph.h> 
void _FAR _setlinestyle( unsigned short style ); 

Description: The _setlinestyle function sets the current line-style mask to the value of the style argument. 
The line-style mask determines the style by which lines and arcs are drawn.  The mask is treated as an array of 16 bits.  As a line is drawn, a pixel at a time, the bits in this array are cyclically tested.  When a bit in the array is 1, the pixel value for the current point is set using the current color according to the current plotting action; otherwise, the pixel value for the point is left unchanged.  A solid line would result from a value of 0xFFFF and a dashed line would result from a value of 0xF0F0 
The default line style mask is 0xFFFF 

Returns: The _setlinestyle function does not return a value. 

See Also: _getlinestyle, _lineto, _rectangle, _polygon, _setplotaction 

Example: 
#include <conio.h> 
#include <graph.h> 
#define DASHED 0xf0f0 
main() 
{ 
  unsigned old_style; 
  _setvideomode( _VRES16COLOR ); 
  old_style = _getlinestyle(); 
  _setlinestyle( DASHED ); 
  _rectangle( _GBORDER, 100, 100, 540, 380 ); 
  _setlinestyle( old_style ); 
  getch(); 
  _setvideomode( _DEFAULTMODE ); 
} 
produces the following: 
The graphical image cannot be reproduced here. See the printed 
version of the manual. 

Classification: PC Graphics 

Systems: DOS, QNX


### setlocale

Synopsis: 
#include <locale.h> 
char *setlocale( int category, const char *locale ); 

Description: The setlocale function selects a portion of a program's locale according to the category given by category and the locale specified by locale.  A locale affects the collating sequence (the order in which characters compare with one another), the way in which certain character-handling functions operate, the decimal-point character that is used in formatted input/output and string conversion, and the format and names used in the time string produced by the  strftime function. 
Potentially, there may be many such environments.  WATCOM C supports only the "C" locale and so invoking this function will have no effect upon the behavior of a program at present. 
The possible values for the argument category are as follows: 

LC_ALL select entire environment 

LC_COLLATE select collating sequence 

LC_CTYPE select the character-handling 

LC_MONETARY select monetary formatting information 

LC_NUMERIC select the numeric-format environment 

LC_TIME select the time-related environment 
At the start of a program, the equivalent of the following statement is executed. 
  setlocale( LC_ALL, "C" ); 

Returns: If the selection is successful, a string is returned to indicate the locale that was in effect before the function was invoked; otherwise, a NULL pointer is returned. 

See Also: strcoll, strftime, strxfrm 

Example: 
#include <stdio.h> 
#include <string.h> 
#include <locale.h> 
char src[] = { "A sample STRING" }; 
char dst[20]; 
void main() 
 { 
  char *prev_locale; 
  size_t len; 
  /* set native locale */ 
  prev_locale = setlocale( LC_ALL, "" ); 
  printf( "%s\n", prev_locale ); 
  len = strxfrm( dst, src, 20 ); 
  printf( "%s (%u)\n", dst, len ); 
 } 
produces the following: 
C 
A sample STRING (15) 

Classification: ANSI, POSIX 1003.1 

Systems: All


### setmode

Synopsis: 
#include <io.h> 
#include <fcntl.h> 
int setmode( int handle, int mode ); 

Description: The setmode function sets, at the operating system level, the translation mode to be the value of mode for the file whose file handle is given by handle.  The mode, defined in the <fcntl.h> header file, can be one of: 

O_TEXT On input, a carriage-return character that immediately precedes a linefeed character is removed from the data that is read.  On output, a carriage-return character is inserted before each linefeed character. 

O_BINARY Data is read or written unchanged. 

Returns: If successful, the function returns the previous mode that was set for the file; otherwise, -1 is returned.  When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

See Also: chsize, close, creat, dup, dup2, eof, exec Functions, filelength, fileno, fstat, isatty, lseek, open, read, sopen, stat, tell, write, umask 

Example: 
#include <stdio.h> 
#include <fcntl.h> 
#include <io.h> 
void main() 
 { 
  FILE *fp; 
  long count; 
  fp = fopen( "file", "rb" ); 
  if( fp != NULL ) { 
   setmode( fileno( fp ), O_BINARY ); 
   count = 0L; 
   while( fgetc( fp ) != EOF ) ++count; 
   printf( "File contains %lu characters\n", 
       count ); 
   fclose( fp ); 
  } 
 } 

Classification: WATCOM 

Systems: All


### _setpixel, _setpixel_w

Synopsis: 
#include <graph.h> 
short _FAR _setpixel( short x, short y ); 
short _FAR _setpixel_w( double x, double y ); 

Description: The _setpixel function sets the pixel value of the point (x,y) using the current plotting action with the current color.  The _setpixel function uses the view coordinate system.  The _setpixel_w function uses the window coordinate system. 
A pixel value is associated with each point.  The values range from 0 to the number of colors (less one) that can be represented in the palette for the current video mode.  The color displayed at the point is the color in the palette corresponding to the pixel number.  For example, a pixel value of 3 causes the fourth color in the palette to be displayed at the point in question. 

Returns: The _setpixel functions return the previous value of the indicated pixel if the pixel value can be set; otherwise, (-1) is returned. 

See Also: _getpixel, _setcolor, _setplotaction 

Example: 
#include <conio.h> 
#include <graph.h> 
#include <stdlib.h> 
main() 
{ 
  int x, y; 
  unsigned i; 
  _setvideomode( _VRES16COLOR ); 
  _rectangle( _GBORDER, 100, 100, 540, 380 ); 
  for( i = 0; i <= 60000; ++i ) { 
    x = 101 + rand() % 439; 
    y = 101 + rand() % 279; 
    _setcolor( _getpixel( x, y ) + 1 ); 
    _setpixel( x, y ); 
  } 
  getch(); 
  _setvideomode( _DEFAULTMODE ); 
} 

Classification: PC Graphics 

Systems:  _setpixel - DOS, QNX 
_setpixel_w - DOS, QNX


### _setplotaction

Synopsis: 
#include <graph.h> 
short _FAR _setplotaction( short action ); 

Description: The _setplotaction function sets the current plotting action to the value of the action argument. 
The drawing functions cause pixels to be set with a pixel value.  By default, the value to be set is obtained by replacing the original pixel value with the supplied pixel value.  Alternatively, the replaced value may be computed as a function of the original and the supplied pixel values. 
The plotting action can have one of the following values: 

_GPSET replace the original screen pixel value with the supplied pixel value 

_GAND replace the original screen pixel value with the bitwise and of the original pixel value and the supplied pixel value 

_GOR replace the original screen pixel value with the bitwise or of the original pixel value and the supplied pixel value 

_GXOR replace the original screen pixel value with the bitwise exclusive-or of the original pixel value and the supplied pixel value.  Performing this operation twice will restore the original screen contents, providing an efficient method to produce animated effects. 

Returns: The previous value of the plotting action is returned. 

See Also: _getplotaction 

Example: 
#include <conio.h> 
#include <graph.h> 
main() 
{ 
  int old_act; 
  _setvideomode( _VRES16COLOR ); 
  old_act = _getplotaction(); 
  _setplotaction( _GPSET ); 
  _rectangle( _GFILLINTERIOR, 100, 100, 540, 380 ); 
  getch(); 
  _setplotaction( _GXOR ); 
  _rectangle( _GFILLINTERIOR, 100, 100, 540, 380 ); 
  getch(); 
  _setplotaction( old_act ); 
  _setvideomode( _DEFAULTMODE ); 
} 

Classification: PC Graphics 

Systems: DOS, QNX


### _settextalign

Synopsis: 
#include <graph.h> 
void _FAR _settextalign( short horiz, short vert ); 

Description: The _settextalign function sets the current text alignment to the values specified by the arguments horiz and vert.  When text is displayed with the  _grtext function, it is aligned (justified) horizontally and vertically about the given point according to the current text alignment settings. 
The horizontal component of the alignment can have one of the following values: 

_NORMAL use the default horizontal alignment for the current setting of the text path 

_LEFT the text string is left justified at the given point 

_CENTER the text string is centred horizontally about the given point 

_RIGHT the text string is right justified at the given point 
The vertical component of the alignment can have one of the following values: 

_NORMAL use the default vertical alignment for the current setting of the text path 

_TOP the top of the text string is aligned at the given point 

_CAP the cap line of the text string is aligned at the given point 

_HALF the text string is centred vertically about the given point 

_BASE the base line of the text string is aligned at the given point 

_BOTTOM the bottom of the text string is aligned at the given point 
The default is to use _LEFT alignment for the horizontal component unless the text path is _PATH_LEFT, in which case _RIGHT alignment is used.  The default value for the vertical component is _TOP unless the text path is _PATH_UP, in which case _BOTTOM alignment is used. 

Returns: The _settextalign function does not return a value. 

See Also: _grtext, _gettextsettings 

Example: 
#include <conio.h> 
#include <graph.h> 
main() 
{ 
  _setvideomode( _VRES16COLOR ); 
  _grtext( 200, 100, "WATCOM" ); 
  _setpixel( 200, 100 ); 
  _settextalign( _CENTER, _HALF ); 
  _grtext( 200, 200, "Graphics" ); 
  _setpixel( 200, 200 ); 
  getch(); 
  _setvideomode( _DEFAULTMODE ); 
} 
produces the following: 
The graphical image cannot be reproduced here. See the printed 
version of the manual. 

Classification: PC Graphics 

Systems: DOS, QNX


### _settextcolor

Synopsis: 
#include <graph.h> 
short _FAR _settextcolor( short pixval ); 

Description: The _settextcolor function sets the current text color to be the color indicated by the pixel value of the pixval argument.  This is the color value used for displaying text with the  _outtext and  _outmem functions.  Use the  _setcolor function to change the color of graphics output.  The default text color value is set to 7 whenever a new video mode is selected. 
The pixel value pixval is a number in the range 0-31.  Colors in the range 0-15 are displayed normally.  In text modes, blinking colors are specified by adding 16 to the normal color values.  The following table specifies the default colors in color text modes. 
    
   Pixel    Color     Pixel    Color 
   value          value 
    0    Black      8    Gray 
    1    Blue       9    Light Blue 
    2    Green      10    Light Green 
    3    Cyan      11    Light Cyan 
    4    Red       12    Light Red 
    5    Magenta     13    Light Magenta 
    6    Brown      14    Yellow 
    7    White      15    Bright White 

Returns: The _settextcolor function returns the pixel value of the previous text color. 

See Also: _gettextcolor, _outtext, _outmem, _setcolor 

Example: 
#include <conio.h> 
#include <graph.h> 
main() 
{ 
  int old_col; 
  long old_bk; 
  _setvideomode( _TEXTC80 ); 
  old_col = _gettextcolor(); 
  old_bk = _getbkcolor(); 
  _settextcolor( 7 ); 
  _setbkcolor( _BLUE ); 
  _outtext( " WATCOM \nGraphics" ); 
  _settextcolor( old_col ); 
  _setbkcolor( old_bk ); 
  getch(); 
  _setvideomode( _DEFAULTMODE ); 
} 

Classification: PC Graphics 

Systems: DOS, QNX


### _settextcursor

Synopsis: 
#include <graph.h> 
short _FAR _settextcursor( short cursor ); 

Description: The _settextcursor function sets the attribute, or shape, of the cursor in text modes.  The argument cursor specifies the new cursor shape.  The cursor shape is selected by specifying the top and bottom rows in the character matrix.  The high byte of cursor specifies the top row of the cursor; the low byte specifies the bottom row. 
Some typical values for cursor are: 
    
   Cursor      Shape 
   0x0607      normal underline cursor 
   0x0007      full block cursor 
   0x0407      half-height block cursor 
   0x2000      no cursor 

Returns: The _settextcursor function returns the previous cursor shape when the shape is set successfully; otherwise, (-1) is returned. 

See Also: _gettextcursor, _displaycursor 

Example: 
#include <conio.h> 
#include <graph.h> 
main() 
{ 
  int old_shape; 
  old_shape = _gettextcursor(); 
  _settextcursor( 0x0007 ); 
  _outtext( "\nBlock cursor" ); 
  getch(); 
  _settextcursor( 0x0407 ); 
  _outtext( "\nHalf height cursor" ); 
  getch(); 
  _settextcursor( 0x2000 ); 
  _outtext( "\nNo cursor" ); 
  getch(); 
  _settextcursor( old_shape ); 
} 

Classification: PC Graphics 

Systems: DOS, QNX


### _settextorient

Synopsis: 
#include <graph.h> 
void _FAR _settextorient( short vecx, short vecy ); 

Description: The _settextorient function sets the current text orientation to the vector specified by the arguments (vecx,vecy).  The text orientation specifies the direction of the base-line vector when a text string is displayed with the  _grtext function.  The default text orientation, for normal left-to-right text, is the vector (1,0). 

Returns: The _settextorient function does not return a value. 

See Also: _grtext, _gettextsettings 

Example: 
#include <conio.h> 
#include <graph.h> 
main() 
{ 
  _setvideomode( _VRES16COLOR ); 
  _grtext( 200, 100, "WATCOM" ); 
  _settextorient( 1, 1 ); 
  _grtext( 200, 200, "Graphics" ); 
  getch(); 
  _setvideomode( _DEFAULTMODE ); 
} 
produces the following: 
The graphical image cannot be reproduced here. See the printed 
version of the manual. 

Classification: PC Graphics 

Systems: DOS, QNX


### _settextpath

Synopsis: 
#include <graph.h> 
void _FAR _settextpath( short path ); 

Description: The _settextpath function sets the current text path to have the value of the path argument.  The text path specifies the writing direction of the text displayed by the  _grtext function.  The argument can have one of the following values: 

_PATH_RIGHT subsequent characters are drawn to the right of the previous character 

_PATH_LEFT subsequent characters are drawn to the left of the previous character 

_PATH_UP subsequent characters are drawn above the previous character 

_PATH_DOWN subsequent characters are drawn below the previous character 
The default value of the text path is _PATH_RIGHT. 

Returns: The _settextpath function does not return a value. 

See Also: _grtext, _gettextsettings 

Example: 
#include <conio.h> 
#include <graph.h> 
main() 
{ 
  _setvideomode( _VRES16COLOR ); 
  _grtext( 200, 100, "WATCOM" ); 
  _settextpath( _PATH_DOWN ); 
  _grtext( 200, 200, "Graphics" ); 
  getch(); 
  _setvideomode( _DEFAULTMODE ); 
} 
produces the following: 
The graphical image cannot be reproduced here. See the printed 
version of the manual. 

Classification: PC Graphics 

Systems: DOS, QNX


### _settextposition

Synopsis: 
#include <graph.h> 
struct rccoord _FAR _settextposition( short row, 
                   short col ); 

Description: The _settextposition function sets the current output position for text to be (row,col) where this position is in terms of characters, not pixels. 
The text position is relative to the current text window.  It defaults to the top left corner of the screen, (1,1), when a new video mode is selected, or when a new text window is set.  The position is updated as text is drawn with the  _outtext and  _outmem functions. 
Note that the output position for graphics output differs from that for text output.  The output position for graphics output can be set by use of the  _moveto function. 

Returns: The _settextposition function returns, as an rccoord structure, the previous output position for text. 

See Also: _gettextposition, _outtext, _outmem, _settextwindow, _moveto 

Example: 
#include <conio.h> 
#include <graph.h> 
main() 
{ 
  struct rccoord old_pos; 
  _setvideomode( _TEXTC80 ); 
  old_pos = _gettextposition(); 
  _settextposition( 10, 40 ); 
  _outtext( "WATCOM Graphics" ); 
  _settextposition( old_pos.row, old_pos.col ); 
  getch(); 
  _setvideomode( _DEFAULTMODE ); 
} 

Classification: PC Graphics 

Systems: DOS, QNX


### _settextrows

Synopsis: 
#include <graph.h> 
short _FAR _settextrows( short rows ); 

Description: The _settextrows function selects the number of rows of text displayed on the screen.  The number of rows is specified by the argument rows.  Computers equipped with EGA, MCGA and VGA adapters can support different numbers of text rows.  The number of rows that can be selected depends on the current video mode and the type of monitor attached. 
If the argument rows has the value _MAXTEXTROWS, the maximum number of text rows will be selected for the current video mode and hardware configuration.  In text modes the maximum number of rows is 43 for EGA adapters, and 50 for MCGA and VGA adapters.  Some graphics modes will support 43 rows for EGA adapters and 60 rows for MCGA and VGA adapters. 

Returns: The _settextrows function returns the number of screen rows when the number of rows is set successfully; otherwise, zero is returned. 

See Also: _getvideoconfig, _setvideomode, _setvideomoderows 

Example: 
#include <conio.h> 
#include <graph.h> 
#include <stdio.h> 
int valid_rows[] = { 
  14, 25, 28, 30, 
  34, 43, 50, 60 
}; 
main() 
{ 
  int i, j, rows; 
  char buf[ 80 ]; 
  for( i = 0; i < 8; ++i ) { 
    rows = valid_rows[ i ]; 
    if( _settextrows( rows ) == rows ) { 
      for( j = 1; j <= rows; ++j ) { 
        sprintf( buf, "Line %d", j ); 
        _settextposition( j, 1 ); 
        _outtext( buf ); 
      } 
      getch(); 
    } 
  } 
  _setvideomode( _DEFAULTMODE ); 
} 

Classification: PC Graphics 

Systems: DOS, QNX


### _settextwindow

Synopsis: 
#include <graph.h> 
void _FAR _settextwindow( short row1, short col1, 
             short row2, short col2 ); 

Description: The _settextwindow function sets the text window to be the rectangle with a top left corner at (row1,col1) and a bottom right corner at (row2,col2).  These coordinates are in terms of characters not pixels. 
The initial text output position is (1,1).  Subsequent text positions are reported (by the  _gettextposition function) and set (by the  _outtext,  _outmem and  _settextposition functions) relative to this rectangle. 
Text is displayed from the current output position for text proceeding along the current row and then downwards.  When the window is full, the lines scroll upwards one line and then text is displayed on the last line of the window. 

Returns: The _settextwindow function does not return a value. 

See Also: _gettextposition, _outtext, _outmem, _settextposition 

Example: 
#include <conio.h> 
#include <graph.h> 
#include <stdio.h> 
main() 
{ 
  int i; 
  short r1, c1, r2, c2; 
  char buf[ 80 ]; 
  _setvideomode( _TEXTC80 ); 
  _gettextwindow( &r1, &c1, &r2, &c2 ); 
  _settextwindow( 5, 20, 20, 40 ); 
  for( i = 1; i <= 20; ++i ) { 
    sprintf( buf, "Line %d\n", i ); 
    _outtext( buf ); 
  } 
  getch(); 
  _settextwindow( r1, c1, r2, c2 ); 
  _setvideomode( _DEFAULTMODE ); 
} 

Classification: PC Graphics 

Systems: DOS, QNX


### setvbuf

Synopsis: 
#include <stdio.h> 
int setvbuf( FILE *fp, 
       char *buf, 
       int mode, 
       size_t size ); 

Description: The setvbuf function can be used to associate a buffer with the file designated by fp.  If this function is used, it must be called after the file has been opened and before it has been read or written.  The argument mode determines how the file fp will be buffered, as follows: 

_IOFBF causes input/output to be fully buffered. 

_IOLBF causes output to be line buffered (the buffer will be flushed when a new-line character is written, when the buffer is full, or when input is requested. 

_IONBF causes input/output to be completely unbuffered. 
If the argument buf is not NULL, the array to which it points will be used instead of an automatically allocated buffer.  The argument size specifies the size of the array. 

Returns: The setvbuf function returns zero on success, or a non-zero value if an invalid value is given for mode or size. 

See Also: fopen, setbuf 

Example: 
#include <stdio.h> 
#include <stdlib.h> 
void main() 
{ 
 char *buf; 
 FILE *fp; 
 fp = fopen( "file", "r" ); 
 buf = malloc( 1024 ); 
 setvbuf( fp, buf, _IOFBF, 1024 ); 
} 

Classification: ANSI 

Systems: All


### _setvideomode

Synopsis: 
#include <graph.h> 
short _FAR _setvideomode( short mode ); 

Description: The _setvideomode function sets the video mode according to the value of the mode argument.  The value of mode can be one of the following: 
    
   Mode      Type   Size   Colors   Adapter 
   _MAXRESMODE  (graphics mode with highest resolution) 
   _MAXCOLORMODE (graphics mode with most colors) 
   _DEFAULTMODE  (restores screen to original mode) 
   _TEXTBW40    M,T   40 x 25   16  MDPA,HGC,VGA,SVGA 
   _TEXTC40    C,T   40 x 25   16  CGA,EGA,MCGA,VGA,SVGA 
   _TEXTBW80    M,T   80 x 25   16  MDPA,HGC,VGA,SVGA 
   _TEXTC80    C,T   80 x 25   16  CGA,EGA,MCGA,VGA,SVGA 
   _MRES4COLOR   C,G  320 x 200   4  CGA,EGA,MCGA,VGA,SVGA 
   _MRESNOCOLOR  C,G  320 x 200   4  CGA,EGA,MCGA,VGA,SVGA 
   _HRESBW     C,G  640 x 200   2  CGA,EGA,MCGA,VGA,SVGA 
   _TEXTMONO    M,T   80 x 25   16  MDPA,HGC,VGA,SVGA 
   _HERCMONO    M,G  720 x 350   2  HGC 
   _MRES16COLOR  C,G  320 x 200  16  EGA,VGA,SVGA 
   _HRES16COLOR  C,G  640 x 200  16  EGA,VGA,SVGA 
   _ERESNOCOLOR  M,G  640 x 350   4  EGA,VGA,SVGA 
   _ERESCOLOR   C,G  640 x 350  4/16  EGA,VGA,SVGA 
   _VRES2COLOR   C,G  640 x 480   2  MCGA,VGA,SVGA 
   _VRES16COLOR  C,G  640 x 480  16  VGA,SVGA 
   _MRES256COLOR  C,G  320 x 200  256  MCGA,VGA,SVGA 
   _URES256COLOR  C,G  640 x 400  256  SVGA 
   _VRES256COLOR  C,G  640 x 480  256  SVGA 
   _SVRES16COLOR  C,G  800 x 600  16  SVGA 
   _SVRES256COLOR C,G  800 x 600  256  SVGA 
   _XRES16COLOR  C,G  1024 x 768  16  SVGA 
   _XRES256COLOR  C,G  1024 x 768  256  SVGA 
In the preceding table, the Type column contains the following letters: 

M indicates monochrome; multiple colors are shades of grey 

C indicates color 

G indicates graphics mode; size is in pixels 

T indicates text mode; size is in columns and rows of characters 
The Adapter column contains the following codes: 

MDPA IBM Monochrome Display/Printer Adapter 

CGA IBM Color Graphics Adapter 

EGA IBM Enhanced Graphics Adapter 

VGA IBM Video Graphics Array 

MCGA IBM Multi-Color Graphics Array 

HGC Hercules Graphics Adapter 

SVGA SuperVGA adapters 
The modes _MAXRESMODE and _MAXCOLORMODE will select from among the video modes supported by the current graphics adapter the one that has the highest resolution or the greatest number of colors.  The video mode will be selected from the standard modes, not including the SuperVGA modes. 
Selecting a new video mode resets the current output positions for graphics and text to be the top left corner of the screen.  The background color is reset to black and the default color value is set to be one less than the number of colors in the selected mode. 

Returns: The _setvideomode function returns the number of text rows when the new mode is successfully selected; otherwise, zero is returned. 

See Also: _getvideoconfig, _settextrows, _setvideomoderows 

Example: 
#include <conio.h> 
#include <graph.h> 
#include <stdio.h> 
#include <stdlib.h> 
main() 
{ 
  int mode; 
  struct videoconfig vc; 
  char buf[ 80 ]; 
  _getvideoconfig( &vc ); 
  /* select "best" video mode */ 
  switch( vc.adapter ) { 
  case _VGA : 
  case _SVGA : 
    mode = _VRES16COLOR; 
    break; 
  case _MCGA : 
    mode = _MRES256COLOR; 
    break; 
  case _EGA : 
    if( vc.monitor == _MONO ) { 
      mode = _ERESNOCOLOR; 
    } else { 
      mode = _ERESCOLOR; 
    } 
    break; 
  case _CGA : 
    mode = _MRES4COLOR; 
    break; 
  case _HERCULES : 
    mode = _HERCMONO; 
    break; 
  default : 
    puts( "No graphics adapter" ); 
    exit( 1 ); 
  } 
  if( _setvideomode( mode ) ) { 
    _getvideoconfig( &vc ); 
    sprintf( buf, "%d x %d x %d\n", vc.numxpixels, 
             vc.numypixels, vc.numcolors ); 
    _outtext( buf ); 
    getch(); 
    _setvideomode( _DEFAULTMODE ); 
  } 
} 

Classification: PC Graphics 

Systems: DOS, QNX


### _setvideomoderows

Synopsis: 
#include <graph.h> 
short _FAR _setvideomoderows( short mode, short rows ); 

Description: The _setvideomoderows function selects a video mode and the number of rows of text displayed on the screen.  The video mode is specified by the argument mode and is selected with the  _setvideomode function.  The number of rows is specified by the argument rows and is selected with the  _settextrows function. 
Computers equipped with EGA, MCGA and VGA adapters can support different numbers of text rows.  The number of rows that can be selected depends on the video mode and the type of monitor attached. 

Returns: The _setvideomoderows function returns the number of screen rows when the mode and number of rows are set successfully; otherwise, zero is returned. 

See Also: _getvideoconfig, _setvideomode, _settextrows 

Example: 
#include <conio.h> 
#include <graph.h> 
#include <stdio.h> 
main() 
{ 
  int rows; 
  char buf[ 80 ]; 
  rows = _setvideomoderows( _TEXTC80, _MAXTEXTROWS ); 
  if( rows != 0 ) { 
    sprintf( buf, "Number of rows is %d\n", rows ); 
    _outtext( buf ); 
    getch(); 
    _setvideomode( _DEFAULTMODE ); 
  } 
} 

Classification: PC Graphics 

Systems: DOS, QNX


### _setvieworg

Synopsis: 
#include <graph.h> 
struct xycoord _FAR _setvieworg( short x, short y ); 

Description: The _setvieworg function sets the origin of the view coordinate system, (0,0), to be located at the physical point (x,y).  This causes subsequently drawn images to be translated by the amount (x,y). 
Note:  In previous versions of the software, the _setvieworg function was called _setlogorg. 

Returns: The _setvieworg function returns, as an xycoord structure, the physical coordinates of the previous origin. 

See Also: _getviewcoord, _getphyscoord, _setcliprgn, _setviewport 

Example: 
#include <conio.h> 
#include <graph.h> 
main() 
{ 
  _setvideomode( _VRES16COLOR ); 
  _setvieworg( 320, 240 ); 
  _ellipse( _GBORDER, -200, -150, 200, 150 ); 
  getch(); 
  _setvideomode( _DEFAULTMODE ); 
} 

Classification: PC Graphics 

Systems: DOS, QNX


### _setviewport

Synopsis: 
#include <graph.h> 
void _FAR _setviewport( short x1, short y1, 
            short x2, short y2 ); 

Description: The _setviewport function restricts the display of graphics output to the clipping region and then sets the origin of the view coordinate system to be the top left corner of the region.  This region is a rectangle whose opposite corners are established by the physical points (x1,y1) and (x2,y2). 
The _setviewport function does not affect text output using the  _outtext and  _outmem functions.  To control the location of text output, see the  _settextwindow function. 

Returns: The _setviewport function does not return a value. 

See Also: _setcliprgn, _setvieworg, _settextwindow, _setwindow 

Example: 
#include <conio.h> 
#include <graph.h> 
#define XSIZE 380 
#define YSIZE 280 
main() 
{ 
  _setvideomode( _VRES16COLOR ); 
  _setviewport( 130, 100, 130 + XSIZE, 100 + YSIZE ); 
  _ellipse( _GBORDER, 0, 0, XSIZE, YSIZE ); 
  getch(); 
  _setvideomode( _DEFAULTMODE ); 
} 

Classification: PC Graphics 

Systems: DOS, QNX


### _setvisualpage

Synopsis: 
#include <graph.h> 
short _FAR _setvisualpage( short pagenum ); 

Description: The _setvisualpage function selects the page (in memory) from which graphics output is displayed.  The page to be selected is given by the pagenum argument. 
Only some combinations of video modes and hardware allow multiple pages of graphics to exist.  When multiple pages are supported, the active page may differ from the visual page.  The graphics information in the visual page determines what is displayed upon the screen.  Animation may be accomplished by alternating the visual page.  A graphics page can be constructed without affecting the screen by setting the active page to be different than the visual page. 
The number of available video pages can be determined by using the  _getvideoconfig function.  The default video page is 0. 

Returns: The _setvisualpage function returns the number of the previous page when the visual page is set successfully; otherwise, a negative number is returned. 

See Also: _getvisualpage, _setactivepage, _getactivepage, _getvideoconfig 

Example: 
#include <conio.h> 
#include <graph.h> 
main() 
{ 
  int old_apage; 
  int old_vpage; 
  _setvideomode( _HRES16COLOR ); 
  old_apage = _getactivepage(); 
  old_vpage = _getvisualpage(); 
  /* draw an ellipse on page 0 */ 
  _setactivepage( 0 ); 
  _setvisualpage( 0 ); 
  _ellipse( _GFILLINTERIOR, 100, 50, 540, 150 ); 
  /* draw a rectangle on page 1 */ 
  _setactivepage( 1 ); 
  _rectangle( _GFILLINTERIOR, 100, 50, 540, 150 ); 
  getch(); 
  /* display page 1 */ 
  _setvisualpage( 1 ); 
  getch(); 
  _setactivepage( old_apage ); 
  _setvisualpage( old_vpage ); 
  _setvideomode( _DEFAULTMODE ); 
} 

Classification: PC Graphics 

Systems: DOS, QNX


### _setwindow

Synopsis: 
#include <graph.h> 
short _FAR _setwindow( short invert, 
            double x1, double y1, 
            double x2, double y2 ); 

Description: The _setwindow function defines a window for the window coordinate system.  Window coordinates are specified as a user-defined range of values.  This allows for consistent pictures regardless of the video mode. 
The window is defined as the region with opposite corners established by the points (x1,y1) and (x2,y2).  The argument invert specifies the direction of the y-axis.  If the value is non-zero, the y values increase from the bottom of the screen to the top, otherwise, the y values increase as you move down the screen. 
The window defined by the _setwindow function is displayed in the current viewport.  A viewport is defined by the  _setviewport function. 
By default, the window coordinate system is defined with the point (0.0,0.0) located at the lower left corner of the screen, and the point (1.0,1.0) at the upper right corner. 

Returns: The _setwindow function returns a non-zero value when the window is set successfully; otherwise, zero is returned. 

See Also: _setviewport 

Example: 
#include <conio.h> 
#include <graph.h> 
main() 
{ 
  _setvideomode( _MAXRESMODE ); 
  draw_house( "Default window" ); 
  _setwindow( 1, -0.5, -0.5, 1.5, 1.5 ); 
  draw_house( "Larger window" ); 
  _setwindow( 1, 0.0, 0.0, 0.5, 1.0 ); 
  draw_house( "Left side" ); 
  _setvideomode( _DEFAULTMODE ); 
} 
draw_house( char *msg ) 
{ 
  _clearscreen( _GCLEARSCREEN ); 
  _outtext( msg ); 
  _rectangle_w( _GBORDER, 0.2, 0.1, 0.8, 0.6 ); 
  _moveto_w( 0.1, 0.5 ); 
  _lineto_w( 0.5, 0.9 ); 
  _lineto_w( 0.9, 0.5 ); 
  _arc_w( 0.4, 0.5, 0.6, 0.3, 0.6, 0.4, 0.4, 0.4 ); 
  _rectangle_w( _GBORDER, 0.4, 0.1, 0.6, 0.4 ); 
  getch(); 
} 

Classification: PC Graphics 

Systems: DOS, QNX


### signal

Synopsis: 
#include <signal.h> 
void ( *signal(int sig, void (*func)(int)) )( int ); 

Description: The signal function is used to specify an action to take place when certain conditions are detected while a program executes.  These conditions are defined to be: 

SIGABRT abnormal termination, such as caused by the  abort function 

SIGBREAK an interactive attention (CTRL/BREAK on keyboard) is signalled 

SIGFPE an erroneous floating-point operation occurs (such as division by zero, overflow and underflow) 

SIGILL illegal instruction encountered 

SIGINT an interactive attention (CTRL/C on keyboard) is signalled 

SIGSEGV an illegal memory reference is detected 

SIGTERM a termination request is sent to the program 

SIGUSR1 OS/2 process flag A via DosFlagProcess 

SIGUSR2 OS/2 process flag B via DosFlagProcess 

SIGUSR3 OS/2 process flag C via DosFlagProcess 
An action can be specified for each of the conditions, depending upon the value of the func argument: 

function When func is a function name, that function will be called equivalently to the following code sequence. 
    
     /* "sig_no" is condition being signalled */ 
     signal( sig_no, SIG_DFL ); 
     (*func)( sig_no ); 
The func function may terminate the program by calling the  exit or  abort functions or call the  longjmp function.  Because the next signal will be handled with default handling, the program must again call signal if it is desired to handle the next condition of the type that has been signalled. 
After returning from the signal-catching function, the receiving process will resume execution at the point at which it was interrupted. 
The signal catching function is described as follows: 
    
     void func( int sig_no ) 
     { 
       /* body of function */ 
     } 
Since signal-catching functions are invoked asynchronously with process execution, the type  sig_atomic_t may be used to define variables on which an atomic operation (e.g., incrementation, decrementation) may be performed. 

SIG_DFL This value causes the default action for the condition to occur. 

SIG_IGN This value causes the indicated condition to be ignored. 
When a condition is detected, it may be handled by a program, it may be ignored, or it may be handled by the usual default action (often causing an error message to be printed upon the stderr stream followed by program termination). 
When the program begins execution, the equivalent of 
    
     signal( SIGABRT, SIG_IGN ); 
     signal( SIGFPE, SIG_DFL ); 
     signal( SIGILL, SIG_DFL ); 
     signal( SIGINT, SIG_IGN ); 
     signal( SIGSEGV, SIG_DFL ); 
     signal( SIGTERM, SIG_DFL ); 
is executed. 
A condition can be generated by a program using the  raise function. 

Returns: A return value of  SIG_ERR indicates that the request could not be handled, and  errno is set to the value  EINVAL. 
Otherwise, the previous value of func for the indicated condition is returned. 

See Also: raise 

Example: 
#include <signal.h> 
sig_atomic_t signal_count; 
void MyHandler( int sig_number ) 
 { 
   ++signal_count; 
 } 
void main() 
 { 
  signal( SIGFPE, MyHandler );  /* set own handler */ 
  signal( SIGABRT, SIG_DFL );   /* Default action */ 
  signal( SIGFPE, SIG_IGN );   /* Ignore condition */ 
 } 

Classification: ANSI 

Systems: All


### sin

Synopsis: 
#include <math.h> 
double sin( double x ); 

Description: The  sin function computes the sine of x (measured in radians).  A large magnitude argument may yield a result with little or no significance. 

Returns: The  sin function returns the sine value. 

See Also: acos, asin, atan, atan2, cos, tan 

Example: 
#include <stdio.h> 
#include <math.h> 
void main() 
 { 
  printf( "%f\n", sin(.5) ); 
 } 
produces the following: 
0.479426 

Classification: ANSI 

Systems: All


### sinh

Synopsis: 
#include <math.h> 
double sinh( double x ); 

Description: The  sinh function computes the hyperbolic sine of x.  A range error occurs if the magnitude of x is too large. 

Returns: The  sinh function returns the hyperbolic sine value.  When the argument is outside the permissible range, the  matherr function is called.  Unless the default  matherr function is replaced, it will set the global variable  errno to  ERANGE, and print a "RANGE error" diagnostic message using the  stderr stream. 

See Also: cosh, tanh, matherr 

Example: 
#include <stdio.h> 
#include <math.h> 
void main() 
 { 
  printf( "%f\n", sinh(.5) ); 
 } 
produces the following: 
0.521095 

Classification: ANSI 

Systems: All


### sleep

Synopsis: 
#include <dos.h> 
void sleep( unsigned seconds ); 

Description: The sleep function suspends execution by the specified number of seconds. 

Returns: The sleep function has no return value. 

See Also: delay 

Example: 
/* 
 * The following program sleeps for the 
 * number of seconds specified in argv[1]. 
 */ 
#include <stdlib.h> 
#include <dos.h> 
void main() 
 { 
  unsigned seconds; 
  seconds = (unsigned) strtol( argv[1], NULL, 0 ); 
  sleep( seconds ); 
 } 

Classification: WATCOM 

Systems: All


### sopen

Synopsis: 
#include <io.h> 
#include <fcntl.h> 
#include <sys\stat.h> 
#include <sys\types.h> 
#include <share.h> 
int sopen( const char *filename, 
      int access, int share, ... ); 

Description: The sopen function opens a file at the operating system level for shared access.  The name of the file to be opened is given by filename.  The file will be accessed according to the access mode specified by access.  When the file is to be created, the optional argument must be given which establishes the future access permissions for the file.  Additionally, the sharing mode of the file is given by the share argument.  The optional argument is the file permissions to be used when  O_CREAT flag is on in the access mode. 
The access mode is established by a combination of the bits defined in the <fcntl.h> header file.  The following bits may be set: 

O_RDONLY permit the file to be only read. 

O_WRONLY permit the file to be only written. 

O_RDWR permit the file to be both read and written. 

O_APPEND causes each record that is written to be written at the end of the file. 

O_CREAT has no effect when the file indicated by filename already exists; otherwise, the file is created; 

O_TRUNC causes the file to be truncated to contain no data when the file exists; has no effect when the file does not exist. 

O_BINARY causes the file to be opened in binary mode which means that data will be transmitted to and from the file unchanged. 

O_TEXT causes the file to be opened in text mode which means that carriage-return characters are written before any linefeed character that is written and causes carriage-return characters to be removed when encountered during reads. 

O_NOINHERIT indicates that this file is not to be inherited by a child process. 

O_EXCL indicates that this file is to be opened for exclusive access.  If the file exists and  O_CREAT was also specified then the open will fail (i.e., use  O_EXCL to ensure that the file does not already exist). 
When neither  O_TEXT nor  O_BINARY are specified, the default value in the global variable  _fmode is used to set the file translation mode.  When the program begins execution, this variable has a value of  O_TEXT. 
 O_CREAT must be specified when the file does not exist and it is to be written. 
When the file is to be created ( O_CREAT is specified), an additional argument must be passed which contains the file permissions to be used for the new file.  The access permissions for the file or directory are specified as a combination of bits (defined in the <sys\stat.h> header file). 
The following bits define permissions for the owner. 

S_IRWXU Read, write, execute/search 

S_IRUSR Read permission 

S_IWUSR Write permission 

S_IXUSR Execute/search permission 
The following bits define permissions for the group. 

S_IRWXG Read, write, execute/search 

S_IRGRP Read permission 

S_IWGRP Write permission 

S_IXGRP Execute/search permission 
The following bits define permissions for others. 

S_IRWXO Read, write, execute/search 

S_IROTH Read permission 

S_IWOTH Write permission 

S_IXOTH Execute/search permission 
The following bits define miscellaneous permissions used by other implementations. 

S_IREAD is equivalent to S_IRUSR (read permission) 

S_IWRITE is equivalent to S_IWUSR (write permission) 

S_IEXEC is equivalent to S_IXUSR (execute/search permission) 
All files are readable with DOS; however, it is a good idea to set S_IREAD when read permission is intended for the file. 
The sopen function applies the current file permission mask to the specified permissions (see  umask). 
The shared access for the file, share, is established by a combination of bits defined in the <share.h> header file.  The following values may be set: 

SH_COMPAT Set compatibility mode. 

SH_DENYRW Prevent read or write access to the file. 

SH_DENYWR Prevent write access of the file. 

SH_DENYRD Prevent read access to the file. 

SH_DENYNO Permit both read and write access to the file. 
You should consult the technical documentation for the DOS system that you are using for more detailed information about these sharing modes. 

Returns: If successful, sopen returns a handle for the file.  When an error occurs while opening the file, - 1 is returned.  When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

Errors: When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

EACCES Access denied because path specifies a directory or a volume ID, or sharing mode denied due to a conflicting open. 

EMFILE No more handles available (too many open files) 

ENOENT Path or file not found 

See Also: chsize, close, creat, dup, dup2, eof, exec Functions, filelength, fileno, fstat, isatty, lseek, open, read, setmode, stat, tell, write, umask 

Example: 
#include <sys\stat.h> 
#include <sys\types.h> 
#include <fcntl.h> 
#include <share.h> 
void main() 
 { 
  int handle; 
  /* open a file for output          */ 
  /* replace existing file if it exists    */ 
  handle = sopen( "file", 
        O_WRONLY | O_CREAT | O_TRUNC, 
        S_IRUSR | S_IWUSR | S_IRGRP | S_IWGRP, 
        SH_DENYWR ); 
  /* read a file which is assumed to exist  */ 
  handle = sopen( "file", O_RDONLY, SH_DENYWR ); 
  /* append to the end of an existing file  */ 
  /* write a new file if file does not exist */ 
  handle = sopen( "file", 
        O_WRONLY | O_CREAT | O_APPEND, 
        S_IRUSR | S_IWUSR | S_IRGRP | S_IWGRP, 
        SH_DENYWR ); 
 } 

Classification: WATCOM 

Systems: All


### sound

Synopsis: 
#include <i86.h> 
void sound( unsigned frequency ); 

Description: The sound function turns on the PC's speaker at the specified frequency.  The frequency is in Hertz (cycles per second).  The speaker can be turned off by calling the  nosound function after an appropriate amount of time. 

Returns: The sound function has no return value. 

See Also: delay, nosound 

Example: 
#include <i86.h> 
/* 
  The numbers in this table are the timer divisors 
  necessary to produce the pitch indicated in the 
  lowest octave that is supported by the "sound" 
  function. 
  To raise the pitch by N octaves, simply divide the 
  number in the table by 2**N since a pitch which is 
  an octave above another has double the frequency of 
  the original pitch. 
  The frequency obtained by these numbers is given by 
  1193180 / X where X is the number obtained in the 
  table. 
*/ 
unsigned short Notes[] = { 
    19327 ,     /* C b       */ 
    18242 ,     /* C        */ 
    17218 ,     /* C #  ( D b )  */ 
    16252 ,     /* D        */ 
    15340 ,     /* D #  ( E b )  */ 
    14479 ,     /* E   ( F b )  */ 
    13666 ,     /* F   ( E # )  */ 
    12899 ,     /* F #  ( G b )  */ 
    12175 ,     /* G        */ 
    11492 ,     /* G #  ( A b )  */ 
    10847 ,     /* A        */ 
    10238 ,     /* A #  ( B b )  */ 
    9664 ,     /* B   ( C b )  */ 
    9121 ,     /* B #       */ 
    0 
}; 
#define FACTOR  1193180 
#define OCTAVE  4 
void main()       /* play the scale */ 
 { 
  int i; 
  for( i = 0; Notes[i]; ++i ) { 
   sound( FACTOR / (Notes[i] / (1 << OCTAVE)) ); 
   delay( 200 ); 
   nosound(); 
  } 
 } 

Classification: Intel 

Systems: DOS, Win, QNX


### spawn Functions

Synopsis: 
#include <process.h> 
int spawnl(  mode, path, arg0, arg1..., argn, NULL ); 
int spawnle(  mode, path, arg0, arg1..., argn, NULL, envp); 
int spawnlp(  mode, file, arg0, arg1..., argn, NULL ); 
int spawnlpe( mode, file, arg0, arg1..., argn, NULL, envp); 
int spawnv(  mode, path, argv ); 
int spawnve(  mode, path, argv, envp ); 
int spawnvp(  mode, file, argv ); 
int spawnvpe( mode, file, argv, envp ); 
 int     mode;       /* mode for parent    */ 
 const char *path;       /* file name incl. path */ 
 const char *file;       /* file name       */ 
 const char *arg0, ..., *argn; /* arguments       */ 
 char *const argv[];      /* array of arguments  */ 
 char *const envp[];      /* environment strings  */ 

Description: The spawn functions create and execute a new child process, named by pgm.  The value of mode determines how the program is loaded and how the invoking program will behave after the invoked program is initiated: 

P_WAIT The invoked program is loaded into available memory, is executed, and then the original program resumes execution. 

P_NOWAIT Causes the current program to execute concurrently with the new child process. 

P_NOWAITO Causes the current program to execute concurrently with the new child process.  The functions  wait and  cwait are ignored. 

P_OVERLAY The invoked program replaces the original program in memory and is executed.  No return is made to the original program.  This is equivalent to calling the appropriate  exec function.  P_OVERLAY is only supported on those systems that also support the  exec function (see the description of the  exec function for more information). 
The program is located by using the following logic in sequence: 

 1.An attempt is made to locate the program in the current working directory if no directory specification precedes the program name; otherwise, an attempt is made in the specified directory. 

 2.If no file extension is given, an attempt is made to find the program name, in the directory indicated in the first point, with .COM concatenated to the end of the program name. 

 3.If no file extension is given, an attempt is made to find the program name, in the directory indicated in the first point, with .EXE concatenated to the end of the program name. 

 4.When no directory specification is given as part of the program name, the  spawnlp,  spawnlpe,  spawnvp, and  spawnvpe functions will repeat the preceding three steps for each of the directories specified by the  PATH environment variable.  The command 
    
   path c:\myapps;d:\lib\applns 
indicates that the two directories 
    
   c:\myapps 
   d:\lib\applns 
are to be searched.  The DOS PATH command (without any directory specification) will cause the current path definition to be displayed. 
An error is detected when the program cannot be found. 
Arguments are passed to the child process by supplying one or more pointers to character strings as arguments in the spawn call.  These character strings are concatenated with spaces inserted to separate the arguments to form one argument string for the child process.  The length of this concatenated string must not exceed 128 bytes for DOS systems. 
The arguments may be passed as a list of arguments ( spawnl,  spawnle,  spawnlp and  spawnlpe) or as a vector of pointers ( spawnv,  spawnve,  spawnvp, and  spawnvpe).  At least one argument, arg0 or argv[0], must be passed to the child process.  By convention, this first argument is a pointer to the name of the program. 
If the arguments are passed as a list, there must be a NULL pointer to mark the end of the argument list.  Similarly, if a pointer to an argument vector is passed, the argument vector must be terminated by a NULL pointer. 
The environment for the invoked program is inherited from the parent process when you use the  spawnl,  spawnlp,  spawnv and  spawnvp functions.  The  spawnle,  spawnlpe,  spawnve and  spawnvpe functions allow a different environment to be passed to the child process through the envp argument.  The argument envp is a pointer to an array of character pointers, each of which points to a string defining an environment variable.  The array is terminated with a NULL pointer.  Each pointer locates a character string of the form 
    
     variable=value 
that is used to define an environment variable.  If the value of envp is NULL, then the child process inherits the environment of the parent process. 
The environment is the collection of environment variables whose values that have been defined with the DOS SET command or by the successful execution of the  putenv function.  A program may read these values with the  getenv function. 

Returns: When the value of mode is  P_WAIT, then the return value from spawn is the exit status of the child process. 
When the value of mode is  P_NOWAIT or  P_NOWAITO, then the return value from spawn is the process id of the child process.  To obtain the exit code for a process spawned with  P_NOWAIT, you must call the  wait or  cwait function specifying the process id.  The exit code cannot be obtained for a process spawned with  P_NOWAITO. 
When an error is detected while invoking the indicated program, spawn returns -1 and  errno is set to indicate the error. 

Errors: When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

E2BIG The argument list exceeds 128 bytes, or the space required for the environment information exceeds 32K. 

EINVAL The mode argument is invalid. 

ENOENT Path or file not found 

ENOMEM Not enough memory is available to execute the child process. 

See Also: abort, atexit, cwait, exec Functions, exit, _exit, getcmd, getenv, main, putenv, system, wait 

Example: 
#include <stddef.h> 
#include <process.h> 
spawnl( P_WAIT, "myprog", 
    "myprog", "ARG1", "ARG2", NULL ); 
The preceding invokes "myprog" as if 
  myprog ARG1 ARG2 
had been entered as a command to DOS.  The program will be found if one of 
  myprog. 
  myprog.com 
  myprog.exe 
is found in the current working directory. 
#include <stddef.h> 
#include <process.h> 
char *env_list[] = { "SOURCE=MYDATA", 
           "TARGET=OUTPUT", 
           "lines=65", 
           NULL 
          }; 
spawnle( P_WAIT, "myprog", 
    "myprog", "ARG1", "ARG2", NULL, 
     env_list ); 
The preceding invokes "myprog" as if 
  myprog ARG1 ARG2 
had been entered as a command to DOS.  The program will be found if one of 
  myprog. 
  myprog.com 
  myprog.exe 
is found in the current working directory.  The DOS environment for the invoked program will consist of the three environment variables SOURCE, TARGET and lines. 
#include <stddef.h> 
#include <process.h> 
char *arg_list[] = { "myprog", "ARG1", "ARG2", NULL }; 
spawnv( P_WAIT, "myprog", arg_list ); 
The preceding invokes "myprog" as if 
  myprog ARG1 ARG2 
had been entered as a command to DOS.  The program will be found if one of 
  myprog. 
  myprog.com 
  myprog.exe 
is found in the current working directory. 

Classification: WATCOM 

Systems:  spawnl - DOS, QNX, OS/2 1.x(all), OS/2 2.x, NT 
spawnle - DOS, QNX, OS/2 1.x(all), OS/2 2.x, NT 
spawnlp - DOS, QNX, OS/2 1.x(all), OS/2 2.x, NT 
spawnlpe - DOS, QNX, OS/2 1.x(all), OS/2 2.x, NT 
spawnv - DOS, QNX, OS/2 1.x(all), OS/2 2.x, NT 
spawnve - DOS, QNX, OS/2 1.x(all), OS/2 2.x, NT 
spawnvp - DOS, QNX, OS/2 1.x(all), OS/2 2.x, NT 
spawnvpe - DOS, QNX, OS/2 1.x(all), OS/2 2.x, NT


### _splitpath

Synopsis: 
#include <stdlib.h> 
void _splitpath( const char *path, 
            char *drive, 
            char *dir, 
            char *fname, 
            char *ext ); 

Description: The _splitpath function splits up a full pathname into four components consisting of a drive letter, directory path, file name and file name extension.  The argument path points to a buffer containing the full pathname to be split up. 
The maximum size required for each buffer is specified by the manifest constants  _MAX_PATH,  _MAX_DRIVE,  _MAX_DIR,  _MAX_FNAME, and  _MAX_EXT which are defined in <stdlib.h>. 

drive The drive argument points to a buffer that will be filled in with the drive letter (e.g., A, B, C, etc.) followed by a colon if a drive is specified in the full pathname (filled in by _splitpath). 

dir The dir argument points to a buffer that will be filled in with the pathname including the trailing slash.  Either forward slashes (/) or backslashes (\) may be used. 

fname The fname argument points to a buffer that will be filled in with the base name of the file without any extension (suffix) if a file name is specified in the full pathname (filled in by _splitpath). 

ext The ext argument points to a buffer that will be filled in with the filename extension (suffix) including the leading period if an extension is specified in the full pathname (filled in by _splitpath). 
The arguments drive, dir, fname and ext will not be filled in if they are NULL pointers. 
For each component of the full pathname that is not present, its corresponding buffer will be set to an empty string. 

Returns: The _splitpath function returns no value. 

See Also: _fullpath, _makepath, _splitpath2 

Example: 
#include <stdio.h> 
#include <stdlib.h> 
void main() 
 { 
  char full_path[ _MAX_PATH ]; 
  char drive[ _MAX_DRIVE ]; 
  char dir[ _MAX_DIR ]; 
  char fname[ _MAX_FNAME ]; 
  char ext[ _MAX_EXT ]; 
  _makepath(full_path,"c","watcomc\\h\\","stdio","h"); 
  printf( "Full path is: %s\n\n", full_path ); 
  _splitpath( full_path, drive, dir, fname, ext ); 
  printf( "Components after _splitpath\n" ); 
  printf( "drive: %s\n", drive ); 
  printf( "dir:  %s\n", dir ); 
  printf( "fname: %s\n", fname ); 
  printf( "ext:  %s\n", ext ); 
 } 
produces the following: 
Full path is: c:watcomc\h\stdio.h 
Components after _splitpath 
drive: c: 
dir:  watcomc\h\ 
fname: stdio 
ext:  .h 
Note the use of two adjacent backslash characters (\) within character-string constants to signify a single backslash. 

Classification: WATCOM 

Systems: All


### _splitpath2

Synopsis: 
#include <stdlib.h> 
void _splitpath2( const char *inp, 
         const char *outp, 
            char **drive, 
            char **dir, 
            char **fname, 
            char **ext ); 

Description: The _splitpath2 function splits up a full pathname into four components consisting of a drive letter, directory path, file name and file name extension. 

inp The argument inp points to a buffer containing the full pathname to be split up. 

outp The argument outp points to a buffer that will contain all the components of the path, each separated by a null character.  The maximum size required for this buffer is specified by the manifest constant  _MAX_PATH2 which is defined in <stdlib.h>. 

drive The drive argument is the location that is to contain the pointer to the drive letter (e.g., A, B, C, etc.) followed by a colon if a drive is specified in the full pathname (filled in by _splitpath2). 

dir The dir argument is the location that is to contain the pointer to the directory path including the trailing slash if a directory path is specified in the full pathname (filled in by _splitpath2).  Either forward slashes (/) or backslashes (\) may be used. 

fname The fname argument is the location that is to contain the pointer to the base name of the file without any extension (suffix) if a file name is specified in the full pathname (filled in by _splitpath2). 

ext The ext argument is the location that is to contain the pointer to the filename extension (suffix) including the leading period if an extension is specified in the full pathname (filled in by _splitpath2). 
The arguments drive, dir, fname and ext will not be filled in if they are NULL pointers. 
For each component of the full pathname that is not present, its corresponding pointer will be set to point at a NULL string ('\0'). 
This function reduces the amount of memory space required when compared to the  splitpath function. 

Returns: The _splitpath2 function returns no value. 

See Also: _fullpath, _makepath, _splitpath 

Example: 
#include <stdio.h> 
#include <stdlib.h> 
void main() 
 { 
  char full_path[ _MAX_PATH ]; 
  char tmp_path[ _MAX_PATH2 ]; 
  char *drive; 
  char *dir; 
  char *fname; 
  char *ext; 
  _makepath(full_path,"c","watcomc\\h","stdio","h"); 
  printf( "Full path is: %s\n\n", full_path ); 
  _splitpath2( full_path, tmp_path, 
         &drive, &dir, &fname, &ext ); 
  printf( "Components after _splitpath2\n" ); 
  printf( "drive: %s\n", drive ); 
  printf( "dir:  %s\n", dir ); 
  printf( "fname: %s\n", fname ); 
  printf( "ext:  %s\n", ext ); 
 } 
produces the following: 
Full path is: c:watcomc\h\stdio.h 
Components after _splitpath2 
drive: c: 
dir:  watcomc\h\ 
fname: stdio 
ext:  .h 
Note the use of two adjacent backslash characters (\) within character-string constants to signify a single backslash. 

Classification: WATCOM 

Systems: All


### sprintf

Synopsis: 
#include <stdio.h> 
int sprintf( char *buf, const char *format, ... ); 

Description: The sprintf function is equivalent to the  fprintf function, except that the argument buf specifies a character array into which the generated output is placed, rather than to a file.  A null character is placed at the end of the generated character string.  The format string is described under the description of the  printf function. 

Returns: The sprintf function returns the number of characters written into the array, not counting the terminating null character.  An error can occur while converting a value for output.  When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

See Also: _bprintf, cprintf, fprintf, printf, _vbprintf, vcprintf, vfprintf, vprintf, vsprintf 

Example: 
To create temporary file names using a counter: 
#include <stdio.h> 
char namebuf[13]; 
int  TempCount = 0; 
char *make_temp_name() 
 { 
  sprintf( namebuf, "ZZ%.6o.TMP", TempCount++ ); 
  return( namebuf ); 
 } 
void main() 
 { 
  FILE *tf1, *tf2; 
  tf1 = fopen( make_temp_name(), "w" ); 
  tf2 = fopen( make_temp_name(), "w" ); 
  fputs( "temp file 1", tf1 ); 
  fputs( "temp file 2", tf2 ); 
  fclose( tf1 ); 
  fclose( tf2 ); 
 } 

Classification: ANSI 

Systems: All


### sqrt

Synopsis: 
#include <math.h> 
double sqrt( double x ); 

Description: The  sqrt function computes the non-negative square root of x.  A domain error occurs if the argument is negative. 

Returns: The  sqrt function returns the value of the square root.  When the argument is outside the permissible range, the  matherr function is called.  Unless the default  matherr function is replaced, it will set the global variable  errno to  EDOM, and print a "DOMAIN error" diagnostic message using the  stderr stream. 

See Also: exp, log, pow, matherr 

Example: 
#include <stdio.h> 
#include <math.h> 
void main() 
 { 
  printf( "%f\n", sqrt(.5) ); 
 } 
produces the following: 
0.707107 

Classification: ANSI 

Systems: All


### srand

Synopsis: 
#include <stdlib.h> 
void srand( unsigned int seed ); 

Description: The srand function uses the argument seed to start a new sequence of pseudo-random integers to be returned by subsequent calls to  rand.  A particular sequence of pseudo-random integers can be repeated by calling  srand with the same seed value.  The default sequence of pseudo-random integers is selected with a seed value of 1. 

Returns: The  srand function returns no value. 

See Also: rand 

Example: 
#include <stdio.h> 
#include <stdlib.h> 
void main() 
 { 
  int i; 
  srand( 982 ); 
  for( i = 1; i < 10; ++i ) { 
    printf( "%d\n", rand() ); 
  } 
  srand( 982 );  /* start sequence over again */ 
  for( i = 1; i < 10; ++i ) { 
    printf( "%d\n", rand() ); 
  } 
 } 

Classification: ANSI 

Systems: All


### sscanf

Synopsis: 
#include <stdio.h> 
int sscanf( const char *in_string, 
      const char *format, ... ); 

Description: The sscanf function scans input from the character string in_string under control of the argument format.  Following the format string is the list of addresses of items to receive values. 
The format string is described under the description of the  scanf function. 

Returns: The sscanf function returns  EOF when the scanning is terminated by reaching the end of the input string.  Otherwise, the number of input arguments for which values were successfully scanned and stored is returned. 

See Also: cscanf, fscanf, scanf, vcscanf, vfscanf, vscanf, vsscanf 

Example: 
To scan the date in the form "Saturday April 18 1987": 
#include <stdio.h> 
void main() 
 { 
  int day, year; 
  char weekday[20], month[20]; 
  sscanf( "Friday August 0014 1987", 
      "%s %s %d  %d", 
       weekday, month, &day, &year ); 
  printf( "%s %s %d %d\n", 
       weekday, month, day, year ); 
 } 
produces the following: 
Friday August 14 1987 

Classification: ANSI 

Systems: All


### stackavail

Synopsis: 
#include <malloc.h> 
size_t stackavail(void); 

Description: The stackavail function returns the number of bytes currently available in the stack.  This value is usually used to determine an appropriate amount to allocate using alloca. 

Returns: The stackavail function returns the number of bytes currently available in the stack. 

See Also: alloca, calloc Functions, malloc Functions 

Example: 
#include <stdio.h> 
#include <string.h> 
#include <malloc.h> 
#include <fcntl.h> 
#include <io.h> 
long char_count( FILE *fp ) 
 { 
   char *buffer; 
   size_t bufsiz; 
   long count; 
   /* allocate half of stack for temp buffer */ 
   bufsiz = stackavail() >> 1; 
   buffer = (char *) alloca( bufsiz ); 
   setvbuf( fp, buffer, _IOFBF, bufsiz ); 
   count = 0L; 
   while( fgetc( fp ) != EOF ) ++count; 
   fclose( fp ); 
   return( count ); 
 } 
void main() 
 { 
  FILE *fp; 
  fp = fopen( "file", "rb" ); 
  if( fp != NULL ) { 
   setmode( fileno( fp ), O_BINARY ); 
   printf( "File contains %lu characters\n", 
     char_count( fp ) ); 
   fclose( fp ); 
  } 
 } 

Classification: WATCOM 

Systems: All


### stat

Synopsis: 
#include <sys\stat.h> 
int stat( const char *path, struct stat *buf ); 

Description: The stat function obtains information about the file or directory referenced in path.  This information is placed in the structure located at the address indicated by buf. 
The file <sys\stat.h> contains definitions for the structure  stat. 
struct stat { 
  dev_t  st_dev;   /* disk drive file resides on */ 
  ino_t  st_ino;   /* this inode's number     */ 
  unsigned short st_mode; /* file mode       */ 
  short  st_nlink;  /* # of hard links       */ 
  short  st_uid;   /* user-id, always 'root'   */ 
  short  st_gid;   /* group-id, always 'root'   */ 
  dev_t  st_rdev;  /* drive #, same as st_dev   */ 
  off_t  st_size;  /* total file size       */ 
  time_t  st_atime;  /* time of last access     */ 
  time_t  st_mtime;  /* time of last modification  */ 
  time_t  st_ctime;  /* time of last status change */ 
}; 
At least the following macros are defined in the <sys\stat.h> header file. 

S_ISFIFO(m) Test for FIFO. 

S_ISCHR(m) Test for character special file. 

S_ISDIR(m) Test for directory file. 

S_ISBLK(m) Test for block special file. 

S_ISREG(m) Test for regular file. 
The value m supplied to the macros is the value of the  st_mode field of a  stat structure.  The macro evaluates to a non-zero value if the test is true and zero if the test is false. 
The following bits are encoded within the  st_mode field of a  stat structure. 

S_IRWXU Read, write, search (if a directory), or execute (otherwise) 

S_IRUSR Read permission bit 

S_IWUSR Write permission bit 

S_IXUSR Search/execute permission bit 

S_IREAD ==  S_IRUSR (for Microsoft compatibility) 

S_IWRITE ==  S_IWUSR (for Microsoft compatibility) 

S_IEXEC ==  S_IXUSR (for Microsoft compatibility) 
 S_IRWXU is the bitwise inclusive OR of  S_IRUSR,  S_IWUSR, and  S_IXUSR. 

S_IRWXG Read, write, search (if a directory), or execute (otherwise) 

S_IRGRP Read permission bit 

S_IWGRP Write permission bit 

S_IXGRP Search/execute permission bit 
 S_IRWXG is the bitwise inclusive OR of  S_IRGRP,  S_IWGRP, and  S_IXGRP. 

S_IRWXO Read, write, search (if a directory), or execute (otherwise) 

S_IROTH Read permission bit 

S_IWOTH Write permission bit 

S_IXOTH Search/execute permission bit 
 S_IRWXO is the bitwise inclusive OR of  S_IROTH,  S_IWOTH, and  S_IXOTH. 

S_ISUID (Not supported by DOS, OS/2 or Windows NT) Set user ID on execution.  The process's effective user ID shall be set to that of the owner of the file when the file is run as a program.  On a regular file, this bit should be cleared on any write. 

S_ISGID (Not supported by DOS, OS/2 or Windows NT) Set group ID on execution.  Set effective group ID on the process to the file's group when the file is run as a program.  On a regular file, this bit should be cleared on any write. 

Returns: The stat function returns zero when the information is successfully obtained.  Otherwise, -1 is returned. 

Errors: When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

EACCES Search permission is denied for a component of path. 

See Also: fstat 

Example: 
#include <stdio.h> 
#include <sys\stat.h> 
void main() 
 { 
  struct stat buf; 
  if( stat( "file", &buf ) != -1 ) { 
   printf( "File size = %d\n", buf.st_size ); 
  } 
 } 

Classification: POSIX 1003.1 

Systems: All


### _status87

Synopsis: 
#include <float.h> 
unsigned int _status87( void ); 

Description: The _status87 function returns the floating-point status word which is used to record the status of 8087/80287/80387/80486 floating-point operations. 

Returns: The _status87 function returns the floating-point status word which is used to record the status of 8087/80287/80387/80486 floating-point operations.  The description of this status is found in the <float.h> header file. 

See Also: _clear87, _control87, _fpreset 

Example: 
#include <stdio.h> 
#include <float.h> 
#define TEST_FPU(x,y) printf( "\t%s " y "\n", \ 
        ((fp_status & x) ? "  " : "No") ) 
void main() 
 { 
  unsigned int fp_status; 
  fp_status = _status87(); 
  printf( "80x87 status\n" ); 
  TEST_FPU( SW_INVALID, "invalid operation" ); 
  TEST_FPU( SW_DENORMAL, "denormalized operand" ); 
  TEST_FPU( SW_ZERODIVIDE, "divide by zero" ); 
  TEST_FPU( SW_OVERFLOW, "overflow" ); 
  TEST_FPU( SW_UNDERFLOW, "underflow" ); 
  TEST_FPU( SW_INEXACT, "inexact result" ); 
 } 

Classification: Intel 

Systems: All


### strcat, _fstrcat

Synopsis: 
#include <string.h> 
char *strcat( char *dst, const char *src ); 
char __far *_fstrcat( char __far *dst, 
           const char __far *src ); 

Description: The strcat and _fstrcat functions append a copy of the string pointed to by src (including the terminating null character) to the end of the string pointed to by dst.  The first character of src overwrites the null character at the end of dst. 
The _fstrcat function is a data model independent form of the strcat function.  It accepts far pointer arguments and returns a far pointer.  It is most useful in mixed memory model applications. 

Returns: The value of dst is returned. 

See Also: strncat 

Example: 
#include <stdio.h> 
#include <string.h> 
void main() 
 { 
  char buffer[80]; 
  strcpy( buffer, "Hello " ); 
  strcat( buffer, "world" ); 
  printf( "%s\n", buffer ); 
 } 
produces the following: 
Hello world 

Classification: strcat is ANSI, _fstrcat is not ANSI 

Systems:  strcat - All 
_fstrcat - All


### strchr, _fstrchr

Synopsis: 
#include <string.h> 
char *strchr( const char *s, int c ); 
char __far *_fstrchr( const char __far *s, int c ); 

Description: The strchr and _fstrchr functions locate the first occurrence of c (converted to a char) in the string pointed to by s.  The terminating null character is considered to be part of the string. 
The _fstrchr function is a data model independent form of the strchr function.  It accepts far pointer arguments and returns a far pointer.  It is most useful in mixed memory model applications. 

Returns: The strchr and _fstrchr functions return a pointer to the located character, or NULL if the character does not occur in the string. 

See Also: memchr, strcspn, strrchr, strspn, strstr, strtok 

Example: 
#include <stdio.h> 
#include <string.h> 
void main() 
 { 
  char buffer[80]; 
  char *where; 
  strcpy( buffer, "video x-rays" ); 
  where = strchr( buffer, 'x' ); 
  if( where == NULL ) { 
    printf( "'x' not found\n" ); 
  } 
 } 

Classification: strchr is ANSI, _fstrchr is not ANSI 

Systems:  strchr - All 
_fstrchr - All


### strcmp, _fstrcmp

Synopsis: 
#include <string.h> 
int strcmp( const char *s1, const char *s2 ); 
int _fstrcmp( const char __far *s1, 
       const char __far *s2 ); 

Description: The strcmp and _fstrcmp functions compare the string pointed to by s1 to the string pointed to by s2. 
The _fstrcmp function is a data model independent form of the strcmp function that accepts far pointer arguments.  It is most useful in mixed memory model applications. 

Returns: The strcmp and _fstrcmp functions return an integer less than, equal to, or greater than zero, indicating that the string pointed to by s1 is less than, equal to, or greater than the string pointed to by s2. 

See Also: stricmp, strncmp, strnicmp 

Example: 
#include <stdio.h> 
#include <string.h> 
void main() 
 { 
  printf( "%d\n", strcmp( "abcdef", "abcdef" ) ); 
  printf( "%d\n", strcmp( "abcdef", "abc" ) ); 
  printf( "%d\n", strcmp( "abc", "abcdef" ) ); 
  printf( "%d\n", strcmp( "abcdef", "mnopqr" ) ); 
  printf( "%d\n", strcmp( "mnopqr", "abcdef" ) ); 
 } 
produces the following: 
0 
1 
-1 
-1 
1 

Classification: strcmp is ANSI, _fstrcmp is not ANSI 

Systems:  strcmp - All 
_fstrcmp - All


### strcmpi

Synopsis: 
#include <string.h> 
int strcmpi( const char *s1, const char *s2 ); 

Description: The strcmpi function compares, with case insensitivity, the string pointed to by s1 to the string pointed to by s2.  All uppercase characters from s1 and s2 are mapped to lowercase for the purposes of doing the comparison.  The strcmpi function is identical to the  stricmp function. 

Returns: The strcmpi function returns an integer less than, equal to, or greater than zero, indicating that the string pointed to by s1 is less than, equal to, or greater than the string pointed to by s2. 

See Also: strcmp, stricmp, strncmp, strnicmp 

Example: 
#include <stdio.h> 
#include <string.h> 
void main() 
 { 
  printf( "%d\n", strcmpi( "AbCDEF", "abcdef" ) ); 
  printf( "%d\n", strcmpi( "abcdef", "ABC"   ) ); 
  printf( "%d\n", strcmpi( "abc",   "ABCdef" ) ); 
  printf( "%d\n", strcmpi( "Abcdef", "mnopqr" ) ); 
  printf( "%d\n", strcmpi( "Mnopqr", "abcdef" ) ); 
 } 
produces the following: 
0 
100 
-100 
-12 
12 

Classification: WATCOM 

Systems: All


### strcoll

Synopsis: 
#include <string.h> 
int strcoll( const char *s1, 
       const char *s2 ); 

Description: The  strcoll function compares the string pointed to by s1 to the string pointed to by s2.  The comparison uses the collating sequence selected by the  setlocale function.  The function will be equivalent to the  strcmp function when the collating sequence is selected from the "C" locale. 

Returns: The strcoll function returns an integer less than, equal to, or greater than zero, indicating that the string pointed to by s1 is less than, equal to, or greater than the string pointed to by s2, according to the collating sequence selected. 

See Also: setlocale, strncmp 

Example: 
#include <stdio.h> 
#include <string.h> 
char buffer[80] = "world"; 
void main() 
 { 
  if( strcoll( buffer, "Hello" ) < 0 ) { 
    printf( "Less than\n" ); 
  } 
 } 

Classification: ANSI 

Systems: All


### strcpy, _fstrcpy

Synopsis: 
#include <string.h> 
char *strcpy( char *dst, const char *src ); 
char __far *_fstrcpy( char __far *dst, 
           const char __far *src ); 

Description: The strcpy and _fstrcpy functions copy the string pointed to by src (including the terminating null character) into the array pointed to by dst.  Copying of overlapping objects is not guaranteed to work properly.  See the description for the  memmove function to copy objects that overlap. 
The _fstrcpy function is a data model independent form of the strcpy function.  It accepts far pointer arguments and returns a far pointer.  It is most useful in mixed memory model applications. 

Returns: The value of dst is returned. 

See Also: strdup, strncpy 

Example: 
#include <stdio.h> 
#include <string.h> 
void main() 
 { 
  auto char buffer[80]; 
  strcpy( buffer, "Hello " ); 
  strcat( buffer, "world" ); 
  printf( "%s\n", buffer ); 
 } 
produces the following: 
Hello world 

Classification: strcpy is ANSI, _fstrcpy is not ANSI 

Systems:  strcpy - All 
_fstrcpy - All


### strcspn, _fstrcspn

Synopsis: 
#include <string.h> 
size_t strcspn( const char *str, 
        const char *charset ); 
size_t _fstrcspn( const char __far *str, 
         const char __far *charset ); 

Description: The strcspn and _fstrcspn functions compute the length of the initial segment of the string pointed to by str which consists entirely of characters not from the string pointed to by charset.  The terminating null character is not considered part of str. 
The _fstrcspn function is a data model independent form of the strcspn function that accepts far pointer arguments.  It is most useful in mixed memory model applications. 

Returns: The length of the initial segment is returned. 

See Also: strspn 

Example: 
#include <stdio.h> 
#include <string.h> 
void main() 
 { 
  printf( "%d\n", strcspn( "abcbcadef", "cba" ) ); 
  printf( "%d\n", strcspn( "xxxbcadef", "cba" ) ); 
  printf( "%d\n", strcspn( "123456789", "cba" ) ); 
 } 
produces the following: 
0 
3 
9 

Classification: strcspn is ANSI, _fstrcspn is not ANSI 

Systems:  strcspn - All 
_fstrcspn - All


### strdup, _fstrdup

Synopsis: 
#include <string.h> 
char *strdup( const char *src ); 
char __far *_fstrdup( const char __far *src ); 

Description: The strdup and _fstrdup functions create a duplicate copy of the string pointed to by src and returns a pointer to the new copy. For strdup, the memory for the new string is obtained by using the  malloc function and can be freed using the  free function.  For _fstrdup, the memory for the new string is obtained by using the  _fmalloc function and can be freed using the  _ffree function. 
The _fstrdup function is a data model independent form of the strdup function that accepts far pointer arguments.  It is most useful in mixed memory model applications. 

Returns: The strdup and _fstrdup functions return the pointer to the new copy of the string if successful, otherwise it returns NULL. 

See Also: free, malloc, strcpy, strncpy 

Example: 
#include <stdio.h> 
#include <string.h> 
void main() 
 { 
  char *dup; 
  dup = strdup( "Make a copy" ); 
  printf( "%s\n", dup ); 
 } 

Classification: WATCOM 

Systems:  strdup - All


### strerror

Synopsis: 
#include <string.h> 
char *strerror( int errnum ); 

Description: The  strerror function maps the error number contained in errnum to an error message. 

Returns: The  strerror function returns a pointer to the error message.  The array containing the error string should not be modified by the program.  This array may be overwritten by a subsequent call to the  strerror function. 

See Also: perror 

Example: 
#include <stdio.h> 
#include <string.h> 
#include <errno.h> 
void main() 
 { 
  FILE *fp; 
  fp = fopen( "file.nam", "r" ); 
  if( fp == NULL ) { 
    printf( "Unable to open file: %s\n", 
         strerror( errno ) ); 
  } 
 } 

Classification: ANSI 

Systems: All


### strftime

Synopsis: 
#include <time.h> 
size_t strftime( char *s, 
         size_t maxsize, 
         const char *format, 
         const struct tm *timeptr ); 
struct  tm { 
 int tm_sec;  /* seconds after the minute -- [0,61] */ 
 int tm_min;  /* minutes after the hour  -- [0,59] */ 
 int tm_hour;  /* hours after midnight   -- [0,23] */ 
 int tm_mday;  /* day of the month     -- [1,31] */ 
 int tm_mon;  /* months since January   -- [0,11] */ 
 int tm_year;  /* years since 1900          */ 
 int tm_wday;  /* days since Sunday     -- [0,6]  */ 
 int tm_yday;  /* days since January 1   -- [0,365]*/ 
 int tm_isdst; /* Daylight Savings Time flag */ 
}; 

Description: The strftime function formats the time in the argument timeptr into the array pointed to by the argument s according to the format argument. 
The format string consists of zero or more directives and ordinary characters.  A directive consists of a '%' character followed by a character that determines the substitution that is to take place.  All ordinary characters are copied unchanged into the array.  No more than maxsize characters are placed in the array.  The format directives %D, %h, %n, %r, %t, and %T are from POSIX. 

%a locale's abbreviated weekday name 

%A locale's full weekday name 

%b locale's abbreviated month name 

%B locale's full month name 

%c locale's appropriate date and time representation 

%d day of the month as a decimal number (01-31) 

%D date in the format mm/dd/yy (POSIX) 

%h locale's abbreviated month name (POSIX) 

%H hour (24-hour clock) as a decimal number (00-23) 

%I hour (12-hour clock) as a decimal number (01-12) 

%j day of the year as a decimal number (001-366) 

%m month as a decimal number (01-12) 

%M minute as a decimal number (00-59) 

%n newline character (POSIX) 

%p locale's equivalent of either AM or PM 

%r 12-hour clock time (01-12) using the AM/PM notation in the format HH:MM:SS (AM|PM) (POSIX) 

%S second as a decimal number (00-59) 

%t tab character (POSIX) 

%T 24-hour clock time in the format HH:MM:SS (POSIX) 

%U week number of the year as a decimal number (00-52) where Sunday is the first day of the week 

%w weekday as a decimal number (0-6) where 0 is Sunday 

%W week number of the year as a decimal number (00-52) where Monday is the first day of the week 

%x locale's appropriate date representation 

%X locale's appropriate time representation 

%y year without century as a decimal number (00-99) 

%Y year with century as a decimal number 

%Z timezone name, or by no characters if no timezone exists 

%% character % 
When the %Z directive is specified, the  tzset function is called. 

Returns: If the number of characters to be placed into the array is less than maxsize, the strftime function returns the number of characters placed into the array pointed to by s not including the terminating null character.  Otherwise, zero is returned.  When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

See Also: setlocale, asctime, clock, ctime, difftime, gmtime, localtime, mktime, time, tzset 

Example: 
#include <stdio.h> 
#include <time.h> 
void main() 
 { 
  time_t time_of_day; 
  char buffer[ 80 ]; 
  time_of_day = time( NULL ); 
  strftime( buffer, 80, "Today is %A %B %d, %Y", 
        localtime( &time_of_day ) ); 
  printf( "%s\n", buffer ); 
 } 
produces the following: 
Today is Friday December 25, 1987 

Classification: ANSI, POSIX 

Systems: All


### stricmp, _fstricmp

Synopsis: 
#include <string.h> 
int stricmp( const char *s1, const char *s2 ); 
int _fstricmp( const char __far *s1, 
        const char __far *s2 ); 

Description: The stricmp and _fstricmp functions compare, with case insensitivity, the string pointed to by s1 to the string pointed to by s2.  All uppercase characters from s1 and s2 are mapped to lowercase for the purposes of doing the comparison. 
The _fstricmp function is a data model independent form of the stricmp function that accepts far pointer arguments.  It is most useful in mixed memory model applications. 

Returns: The stricmp and _fstricmp functions return an integer less than, equal to, or greater than zero, indicating that the string pointed to by s1 is less than, equal to, or greater than the string pointed to by s2. 

See Also: strcmp, strcmpi, strncmp, strnicmp 

Example: 
#include <stdio.h> 
#include <string.h> 
void main() 
 { 
  printf( "%d\n", stricmp( "AbCDEF", "abcdef" ) ); 
  printf( "%d\n", stricmp( "abcdef", "ABC"   ) ); 
  printf( "%d\n", stricmp( "abc",   "ABCdef" ) ); 
  printf( "%d\n", stricmp( "Abcdef", "mnopqr" ) ); 
  printf( "%d\n", stricmp( "Mnopqr", "abcdef" ) ); 
 } 
produces the following: 
0 
100 
-100 
-12 
12 

Classification: WATCOM 

Systems:  stricmp - All 
_fstricmp - All


### strlen, _fstrlen

Synopsis: 
#include <string.h> 
size_t strlen( const char *s ); 
size_t _fstrlen( const char __far *s ); 

Description: The strlen and _fstrlen functions compute the length of the string pointed to by s. 
The _fstrlen function is a data model independent form of the strlen function that accepts far pointer arguments.  It is most useful in mixed memory model applications. 

Returns: The strlen and _fstrlen functions return the number of characters that precede the terminating null character. 

Example: 
#include <stdio.h> 
#include <string.h> 
void main() 
 { 
  printf( "%d\n", strlen( "Howdy" ) ); 
  printf( "%d\n", strlen( "Hello world\n" ) ); 
  printf( "%d\n", strlen( "" ) ); 
 } 
produces the following: 
5 
12 
0 

Classification: strlen is ANSI, _fstrlen is not ANSI 

Systems:  strlen - All 
_fstrlen - All


### strlwr, _fstrlwr

Synopsis: 
#include <string.h> 
char *strlwr( char *s1 ); 
char __far *_fstrlwr( char __far *s1 ); 

Description: The strlwr and _fstrlwr functions replace the string s1 with lowercase characters by invoking the  tolower function for each character in the string. 
The _fstrlwr function is a data model independent form of the strlwr function.  It accepts far pointer arguments and returns a far pointer.  It is most useful in mixed memory model applications. 

Returns: The address of the original string s1 is returned. 

See Also: strupr 

Example: 
#include <stdio.h> 
#include <string.h> 
char source[] = { "A mixed-case STRING" }; 
void main() 
 { 
  printf( "%s\n", source ); 
  printf( "%s\n", strlwr( source ) ); 
  printf( "%s\n", source ); 
 } 
produces the following: 
A mixed-case STRING 
a mixed-case string 
a mixed-case string 

Classification: WATCOM 

Systems:  strlwr - All 
_fstrlwr - All


### strncat, _fstrncat

Synopsis: 
#include <string.h> 
char *strncat( char *dst, const char *src, size_t n ); 
char __far *_fstrncat( char __far *dst, 
            const char __far *src, 
            size_t n ); 

Description: The strncat and _fstrncat functions append not more than n characters of the string pointed to by src to the end of the string pointed to by dst.  The first character of src overwrites the null character at the end of dst.  A terminating null character is always appended to the result. 
The _fstrncat function is a data model independent form of the strncat function.  It accepts far pointer arguments and returns a far pointer.  It is most useful in mixed memory model applications. 

Returns: The strncat and _fstrncat functions return the value of dst. 

See Also: strcat 

Example: 
#include <stdio.h> 
#include <string.h> 
char buffer[80]; 
void main() 
 { 
  strcpy( buffer, "Hello " ); 
  strncat( buffer, "world", 8 ); 
  printf( "%s\n", buffer ); 
  strncat( buffer, "*************", 4 ); 
  printf( "%s\n", buffer ); 
 } 
produces the following: 
Hello world 
Hello world**** 

Classification: strncat is ANSI, _fstrncat is not ANSI 

Systems:  strncat - All 
_fstrncat - All


### strncmp, _fstrncmp

Synopsis: 
#include <string.h> 
int strncmp( const char *s1, 
       const char *s2, 
       size_t n ); 
int _fstrncmp( const char __far *s1, 
        const char __far *s2, 
        size_t n ); 

Description: The strncmp and _fstrncmp functions compare not more than n characters from the string pointed to by s1 to the string pointed to by s2. 
The _fstrncmp function is a data model independent form of the strncmp function that accepts far pointer arguments.  It is most useful in mixed memory model applications. 

Returns: The strncmp and _fstrncmp functions return an integer less than, equal to, or greater than zero, indicating that the string pointed to by s1 is less than, equal to, or greater than the string pointed to by s2. 

See Also: strcmp, stricmp, strnicmp 

Example: 
#include <stdio.h> 
#include <string.h> 
void main() 
 { 
  printf( "%d\n", strncmp( "abcdef", "abcDEF", 10 ) ); 
  printf( "%d\n", strncmp( "abcdef", "abcDEF",  6 ) ); 
  printf( "%d\n", strncmp( "abcdef", "abcDEF",  3 ) ); 
  printf( "%d\n", strncmp( "abcdef", "abcDEF",  0 ) ); 
 } 
produces the following: 
1 
1 
0 
0 

Classification: strncmp is ANSI, _fstrncmp is not ANSI 

Systems:  strncmp - All 
_fstrncmp - All


### strncpy, _fstrncpy

Synopsis: 
#include <string.h> 
char *strncpy( char *dst, 
        const char *src, 
        size_t n ); 
char __far *_fstrncpy( char __far *dst, 
            const char __far *src, 
            size_t n ); 

Description: The strncpy and _fstrncpy functions copy no more than n characters from the string pointed to by src into the array pointed to by dst.  Copying of overlapping objects is not guaranteed to work properly.  See the  memmove function if you wish to copy objects that overlap. 
If the string pointed to by src is shorter than n characters, null characters are appended to the copy in the array pointed to by dst, until n characters in all have been written.  If the string pointed to by src is longer than n characters, then the result will not be terminated by a null character. 
The _fstrncpy function is a data model independent form of the strncpy function.  It accepts far pointer arguments and returns a far pointer.  It is most useful in mixed memory model applications. 

Returns: The strncpy and _fstrncpy functions return the value of dst. 

See Also: strcpy, strdup 

Example: 
#include <stdio.h> 
#include <string.h> 
void main() 
 { 
  char buffer[15]; 
  printf( "%s\n", strncpy( buffer, "abcdefg", 10 ) ); 
  printf( "%s\n", strncpy( buffer, "1234567",  6 ) ); 
  printf( "%s\n", strncpy( buffer, "abcdefg",  3 ) ); 
  printf( "%s\n", strncpy( buffer, "*******",  0 ) ); 
 } 
produces the following: 
abcdefg 
123456g 
abc456g 
abc456g 

Classification: strncpy is ANSI, _fstrncpy is not ANSI 

Systems:  strncpy - All 
_fstrncpy - All


### strnicmp, _fstrnicmp

Synopsis: 
#include <string.h> 
int strnicmp( const char *s1, 
       const char *s2, 
       size_t len ); 
int _fstrnicmp( const char __far *s1, 
        const char __far *s2, 
        size_t len ); 

Description: The strnicmp and _fstrnicmp functions compare, without case sensitivity, the string pointed to by s1 to the string pointed to by s2, for at most len characters. 
The _fstrnicmp function is a data model independent form of the strnicmp function that accepts far pointer arguments.  It is most useful in mixed memory model applications. 

Returns: The strnicmp and _fstrnicmp functions return an integer less than, equal to, or greater than zero, indicating that the string pointed to by s1 is less than, equal to, or greater than the string pointed to by s2. 

See Also: strcmp, stricmp, strncmp 

Example: 
#include <stdio.h> 
#include <string.h> 
void main() 
 { 
  printf( "%d\n", strnicmp( "abcdef", "ABCXXX", 10 ) ); 
  printf( "%d\n", strnicmp( "abcdef", "ABCXXX",  6 ) ); 
  printf( "%d\n", strnicmp( "abcdef", "ABCXXX",  3 ) ); 
  printf( "%d\n", strnicmp( "abcdef", "ABCXXX",  0 ) ); 
 } 
produces the following: 
-20 
-20 
0 
0 

Classification: WATCOM 

Systems:  strnicmp - All 
_fstrnicmp - All


### strnset, _fstrnset

Synopsis: 
#include <string.h> 
char *strnset( char *s1, int fill, size_t len ); 
char __far *_fstrnset( char __far *s1, 
            int fill, 
            size_t len ); 

Description: The strnset and _fstrnset functions fill the string s1 with the value of the argument fill, converted to be a character value.  When the value of len is greater than the length of the string, the entire string is filled.  Otherwise, that number of characters at the start of the string are set to the fill character. 
The _fstrnset function is a data model independent form of the strnset function.  It accepts far pointer arguments and returns a far pointer.  It is most useful in mixed memory model applications. 

Returns: The address of the original string s1 is returned. 

See Also: strset 

Example: 
#include <stdio.h> 
#include <string.h> 
char source[] = { "A sample STRING" }; 
void main() 
 { 
  printf( "%s\n", source ); 
  printf( "%s\n", strnset( source, '=', 100 ) ); 
  printf( "%s\n", strnset( source, '*', 7 ) ); 
 } 
produces the following: 
A sample STRING 
=============== 
*******======== 

Classification: WATCOM 

Systems:  strnset - All 
_fstrnset - All


### strpbrk, _fstrpbrk

Synopsis: 
#include <string.h> 
char *strpbrk( const char *str, const char *charset ); 
char __far *_fstrpbrk( const char __far *str, 
            const char __far *charset ); 

Description: The strpbrk and _fstrpbrk functions locate the first occurrence in the string pointed to by str of any character from the string pointed to by charset. 
The _fstrpbrk function is a data model independent form of the strpbrk function.  It accepts far pointer arguments and returns a far pointer.  It is most useful in mixed memory model applications. 

Returns: The strpbrk and _fstrpbrk functions return a pointer to the located character, or NULL if no character from charset occurs in str. 

See Also: strchr, strrchr, strtok 

Example: 
#include <stdio.h> 
#include <string.h> 
void main() 
 { 
  char *p = "Find all vowels"; 
  while( p != NULL ) { 
   printf( "%s\n", p ); 
   p = strpbrk( p+1, "aeiouAEIOU" ); 
  } 
 } 
produces the following: 
Find all vowels 
ind all vowels 
all vowels 
owels 
els 

Classification: strpbrk is ANSI, _fstrpbrk is not ANSI 

Systems:  strpbrk - All 
_fstrpbrk - All


### strrchr, _fstrrchr

Synopsis: 
#include <string.h> 
char *strrchr( const char *s, int c ); 
char __far *_fstrrchr( const char __far *s, int c ); 

Description: The strrchr and _fstrrchr functions locate the last occurrence of c (converted to a char) in the string pointed to by s.  The terminating null character is considered to be part of the string. 
The _fstrrchr function is a data model independent form of the strrchr function.  It accepts far pointer arguments and returns a far pointer.  It is most useful in mixed memory model applications. 

Returns: The strrchr and _fstrrchr functions return a pointer to the located character, or a NULL pointer if the character does not occur in the string. 

See Also: strchr, strpbrk 

Example: 
#include <stdio.h> 
#include <string.h> 
void main() 
 { 
  printf( "%s\n", strrchr( "abcdeabcde", 'a' ) ); 
  if( strrchr( "abcdeabcde", 'x' ) == NULL ) 
    printf( "NULL\n" ); 
 } 
produces the following: 
abcde 
NULL 

Classification: strrchr is ANSI, _fstrrchr is not ANSI 

Systems:  strrchr - All 
_fstrrchr - All


### strrev, _fstrrev

Synopsis: 
#include <string.h> 
char *strrev( char *s1 ); 
char __far *_fstrrev( char __far *s1 ); 

Description: The strrev and _fstrrev functions replace the string s1 with a string whose characters are in the reverse order. 
The _fstrrev function is a data model independent form of the strrev function.  It accepts far pointer arguments and returns a far pointer.  It is most useful in mixed memory model applications. 

Returns: The address of the original string s1 is returned. 

Example: 
#include <stdio.h> 
#include <string.h> 
char source[] = { "A sample STRING" }; 
void main() 
 { 
  printf( "%s\n", source ); 
  printf( "%s\n", strrev( source ) ); 
  printf( "%s\n", strrev( source ) ); 
 } 
produces the following: 
A sample STRING 
GNIRTS elpmas A 
A sample STRING 

Classification: WATCOM 

Systems:  strrev - All 
_fstrrev - All


### strset, _fstrset

Synopsis: 
#include <string.h> 
char *strset( char *s1, int fill ); 
char __far *_fstrset( char __far *s1, int fill ); 

Description: The strset and _fstrset functions fill the string pointed to by s1 with the character fill.  The terminating null character in the original string remains unchanged. 
The _fstrset function is a data model independent form of the strset function.  It accepts far pointer arguments and returns a far pointer.  It is most useful in mixed memory model applications. 

Returns: The address of the original string s1 is returned. 

See Also: strnset 

Example: 
#include <stdio.h> 
#include <string.h> 
char source[] = { "A sample STRING" }; 
void main() 
 { 
  printf( "%s\n", source ); 
  printf( "%s\n", strset( source, '=' ) ); 
  printf( "%s\n", strset( source, '*' ) ); 
 } 
produces the following: 
A sample STRING 
=============== 
*************** 

Classification: WATCOM 

Systems:  strset - All 
_fstrset - All


### strspn, _fstrspn

Synopsis: 
#include <string.h> 
size_t strspn( const char *str, 
        const char *charset ); 
size_t _fstrspn( const char __far *str, 
         const char __far *charset ); 

Description: The strspn and _fstrspn functions compute the length of the initial segment of the string pointed to by str which consists of characters from the string pointed to by charset.  The terminating null character is not considered to be part of charset. 
The _fstrspn function is a data model independent form of the strspn function that accepts far pointer arguments.  It is most useful in mixed memory model applications. 

Returns: The strspn and _fstrspn functions return the length of the segment. 

See Also: strcspn 

Example: 
#include <stdio.h> 
#include <string.h> 
void main() 
 { 
  printf( "%d\n", strspn( "out to lunch", "aeiou" ) ); 
  printf( "%d\n", strspn( "out to lunch", "xyz" ) ); 
 } 
produces the following: 
2 
0 

Classification: strspn is ANSI, _fstrspn is not ANSI 

Systems:  strspn - All 
_fstrspn - All


### strstr, _fstrstr

Synopsis: 
#include <string.h> 
char *strstr( const char *str, 
       const char *substr ); 
char __far *_fstrstr( const char __far *str, 
           const char __far *substr ); 

Description: The strstr and _fstrstr functions locate the first occurrence in the string pointed to by str of the sequence of characters (excluding the terminating null character) in the string pointed to by substr. 
The _fstrstr function is a data model independent form of the strstr function.  It accepts far pointer arguments and returns a far pointer.  It is most useful in mixed memory model applications. 

Returns: The strstr and _fstrstr functions return a pointer to the located string, or NULL if the string is not found. 

See Also: strcspn 

Example: 
#include <stdio.h> 
#include <string.h> 
void main() 
 { 
  printf( "%s\n", 
      strstr( "This is an example", "is" ) 
     ); 
 } 
produces the following: 
is is an example 

Classification: strstr is ANSI, _fstrstr is not ANSI 

Systems:  strstr - All 
_fstrstr - All


### strtod

Synopsis: 
#include <stdlib.h> 
double strtod( const char *ptr, char **endptr ); 

Description: The strtod function converts the string pointed to by ptr to double representation.  The function recognizes a string containing: 

ooptional white space, 
oan optional plus or minus sign, 
oa sequence of digits containing an optional decimal point, 
oan optional 'e' or 'E' followed by an optionally signed sequence of digits. 
The conversion ends at the first unrecognized character.  A pointer to that character will be stored in the object to which endptr points if endptr is not NULL. 

Returns: The  strtod function returns the converted value. If the correct value would cause overflow, plus or minus  HUGE_VAL is returned according to the sign, and  errno is set to  ERANGE.  If the correct value would cause underflow, then zero is returned, and  errno is set to  ERANGE.  Zero is returned when the input string cannot be converted.  When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

See Also: atof 

Example: 
#include <stdio.h> 
#include <stdlib.h> 
void main() 
 { 
  double pi; 
  pi = strtod( "3.141592653589793", NULL ); 
  printf( "pi=%17.15f\n",pi ); 
 } 

Classification: ANSI 

Systems: All


### strtok, _fstrtok

Synopsis: 
#include <string.h> 
char *strtok( char *s1, const char *s2 ); 
char __far *_fstrtok( char __far *s1, 
           const char __far *s2 ); 

Description: The strtok and _fstrtok functions are used to break the string pointed to by s1 into a sequence of tokens, each of which is delimited by a character from the string pointed to by s2.  The first call to strtok will return a pointer to the first token in the string pointed to by s1.  Subsequent calls to strtok must pass a NULL pointer as the first argument, in order to get the next token in the string.  The set of delimiters used in each of these calls to strtok can be different from one call to the next. 
The first call in the sequence searches s1 for the first character that is not contained in the current delimiter string s2.  If no such character is found, then there are no tokens in s1 and the strtok function returns a NULL pointer.  If such a character is found, it is the start of the first token. 
The strtok function then searches from there for a character that is contained in the current delimiter string.  If no such character is found, the current token extends to the end of the string pointed to by s1.  If such a character is found, it is overwritten by a null character, which terminates the current token.  The strtok function saves a pointer to the following character, from which the next search for a token will start when the first argument is a NULL pointer. 
Because strtok may modify the original string, that string should be duplicated if the string is to be re-used. 
The _fstrtok function is a data model independent form of the strtok function.  It accepts far pointer arguments and returns a far pointer.  It is most useful in mixed memory model applications. 

Returns: The strtok and _fstrtok functions return a pointer to the first character of a token or NULL if there is no token found. 

See Also: strcspn, strpbrk 

Example: 
#include <stdio.h> 
#include <string.h> 
void main() 
 { 
  char *p; 
  char *buffer; 
  char *delims = { " .," }; 
  buffer = strdup( "Find words, all of them." ); 
  printf( "%s\n", buffer ); 
  p = strtok( buffer, delims ); 
  while( p != NULL ) { 
   printf( "word: %s\n", p ); 
   p = strtok( NULL, delims ); 
  } 
  printf( "%s\n", buffer ); 
 } 
produces the following: 
Find words, all of them. 
word: Find 
word: words 
word: all 
word: of 
word: them 
Find 

Classification: strtok is ANSI, _fstrtok is not ANSI 

Systems:  strtok - All 
_fstrtok - All


### strtol

Synopsis: 
#include <stdlib.h> 
long int strtol( const char *ptr, 
         char **endptr, 
         int base ); 

Description: The  strtol function converts the string pointed to by ptr to an object of type long int.  The function recognizes a string containing: 

ooptional white space, 
oan optional plus or minus sign, 
oa sequence of digits and letters. 
The conversion ends at the first unrecognized character.  A pointer to that character will be stored in the object to which endptr points if endptr is not NULL. 
If base is zero, the first characters after the optional sign determine the base used for the conversion.  If the first characters are "0x" or "0X" the digits are treated as hexadecimal.  If the first character is '0', the digits are treated as octal.  Otherwise the digits are treated as decimal. 
If base is not zero, it must have a value between 2 and 36.  The letters a-z and A-Z represent the values 10 through 35.  Only those letters whose designated values are less than base are permitted.  If the value of base is 16, the characters "0x" or "0X" may optionally precede the sequence of letters and digits. 

Returns: The strtol function returns the converted value.  If the correct value would cause overflow,  LONG_MAX or  LONG_MIN is returned according to the sign, and  errno is set to  ERANGE.  If base is out of range, zero is returned and  errno is set to  EDOM. 

See Also: ltoa, strtoul 

Example: 
#include <stdlib.h> 
void main() 
 { 
  long int v; 
  v = strtol( "12345678", NULL, 10 ); 
 } 

Classification: ANSI 

Systems: All


### strtoul

Synopsis: 
#include <stdlib.h> 
unsigned long int strtoul( const char *ptr, 
              char **endptr, 
              int base ); 

Description: The strtoul function converts the string pointed to by ptr to an unsigned long.  The function recognizes a string containing optional white space, followed by a sequence of digits and letters.  The conversion ends at the first unrecognized character.  A pointer to that character will be stored in the object endptr points to if endptr is not NULL. 
If base is zero, the first characters determine the base used for the conversion.  If the first characters are "0x" or "0X" the digits are treated as hexadecimal.  If the first character is '0', the digits are treated as octal.  Otherwise the digits are treated as decimal. 
If base is not zero, it must have a value of between 2 and 36.  The letters a-z and A-Z represent the values 10 through 35.  Only those letters whose designated values are less than base are permitted.  If the value of base is 16, the characters "0x" or "0X" may optionally precede the sequence of letters and digits. 

Returns: The strtoul function returns the converted value. If the correct value would cause overflow,  ULONG_MAX is returned and  errno is set to  ERANGE.  If base is out of range, zero is returned and  errno is set to  EDOM. 

See Also: ltoa, strtol, ultoa 

Example: 
#include <stdlib.h> 
void main() 
 { 
  unsigned long int v; 
  v = strtoul( "12345678", NULL, 10 ); 
 } 

Classification: ANSI 

Systems: All


### strupr, _fstrupr

Synopsis: 
#include <string.h> 
char *strupr( char *s1 ); 
char __far *_fstrupr( char __far *s1 ); 

Description: The strupr and _fstrupr functions replace the string s1 with uppercase characters by invoking the  toupper function for each character in the string. 
The _fstrupr function is a data model independent form of the strupr function.  It accepts far pointer arguments and returns a far pointer.  It is most useful in mixed memory model applications. 

Returns: The address of the original string s1 is returned. 

See Also: strlwr 

Example: 
#include <stdio.h> 
#include <string.h> 
char source[] = { "A mixed-case STRING" }; 
void main() 
 { 
  printf( "%s\n", source ); 
  printf( "%s\n", strupr( source ) ); 
  printf( "%s\n", source ); 
 } 
produces the following: 
A mixed-case STRING 
A MIXED-CASE STRING 
A MIXED-CASE STRING 

Classification: WATCOM 

Systems:  strupr - All 
_fstrupr - All


### strxfrm

Synopsis: 
#include <string.h> 
size_t strxfrm( char *dst, 
        const char *src, 
        size_t n ); 

Description: The strxfrm function transforms, for no more than n characters, the string pointed to by src to the buffer pointed to by dst.  The transformation uses the collating sequence selected by the  setlocale function so that two transformed strings will compare identically (using the  strncmp function) to a comparison of the original two strings using the  strcoll function.  The function will be equivalent to the  strncpy function (except there is no padding of the dst argument with null characters when the argument src is shorter than n characters) when the collating sequence is selected from the "C" locale. 

Returns: The strxfrm function returns the length of the transformed string.  If this length is more than n, the contents of the array pointed to by dst are indeterminate. 

See Also: setlocale, strcoll 

Example: 
#include <stdio.h> 
#include <string.h> 
#include <locale.h> 
char src[] = { "A sample STRING" }; 
char dst[20]; 
void main() 
 { 
  size_t len; 
  setlocale( LC_ALL, "C" ); 
  printf( "%s\n", src ); 
  len = strxfrm( dst, src, 20 ); 
  printf( "%s (%u)\n", dst, len ); 
 } 
produces the following: 
A sample STRING 
A sample STRING (15) 

Classification: ANSI 

Systems: All


### swab

Synopsis: 
#include <stdlib.h> 
void swab( char *src, char *dest, int num ); 

Description: The swab function copies num bytes (which should be even) from src to dest swapping every pair of characters.  This is useful for preparing binary data to be transferred to another machine that has a different byte ordering. 

Returns: The swab function has no return value. 

Example: 
#include <stdio.h> 
#include <string.h> 
#include <stdlib.h> 
char *msg = "hTsim seasegi  swspaep.d"; 
#define NBYTES 24 
void main() 
 { 
  auto char buffer[80]; 
  printf( "%s\n", msg ); 
  memset( buffer, '\0', 80 ); 
  swab( msg, buffer, NBYTES ); 
  printf( "%s\n", buffer ); 
 } 
produces the following: 
hTsim seasegi  swspaep.d 
This message is swapped. 

Classification: WATCOM 

Systems: All


### system

Synopsis: 
#include <stdlib.h> 
int system( const char *command ); 

Description: If the value of command is NULL, then the system function determines whether or not a command processor is present (COMMAND.COM in DOS or CMD.EXE in OS/2). 
Otherwise, the  system function invokes a copy of the command processor, and passes the string command to it for processing.  This function uses  spawnl to load a copy of the command processor identified by the  COMSPEC environment variable. 
This means that any command that can be entered to DOS can be executed, including programs, DOS commands and batch files.  The  exec...  and  spawn...  functions can only cause programs to be executed. 

Returns: If the value of command is NULL, then the system function returns zero if the command processor is not present, a non-zero value if the command processor is present.  Note that Microsoft Windows 3.x does not support a command shell and so the system function always returns zero. 
Otherwise, the system function returns the result of invoking a copy of the command processor.  A non-zero value is returned if the command processor could not be loaded; otherwise, zero is returned.  When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

See Also: abort, atexit, _bgetcmd, exec Functions, exit, _exit, getcmd, getenv, main, onexit, putenv, spawn Functions 

Example: 
#include <stdlib.h> 
#include <stdio.h> 
void main() 
 { 
  int rc; 
  rc = system( "dir" ); 
  if( rc != 0 ) { 
   printf( "shell could not be run\n" ); 
  } 
 } 

Classification: ANSI, POSIX 1003.2 

Systems: All


### tan

Synopsis: 
#include <math.h> 
double tan( double x ); 

Description: The tan function computes the tangent of x (measured in radians).  A large magnitude argument may yield a result with little or no significance. 

Returns: The tan function returns the tangent value.  When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

See Also: atan, atan2, cos, sin, tanh 

Example: 
#include <stdio.h> 
#include <math.h> 
void main() 
 { 
  printf( "%f\n", tan(.5) ); 
 } 
produces the following: 
0.546302 

Classification: ANSI 

Systems: All


### tanh

Synopsis: 
#include <math.h> 
double tanh( double x ); 

Description: The  tanh function computes the hyperbolic tangent of x. 
When the x argument is large, partial or total loss of significance may occur.  The  matherr function will be invoked in this case. 

Returns: The  tanh function returns the hyperbolic tangent value.  When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

See Also: cosh, sinh, matherr 

Example: 
#include <stdio.h> 
#include <math.h> 
void main() 
 { 
  printf( "%f\n", tanh(.5) ); 
 } 
produces the following: 
0.462117 

Classification: ANSI 

Systems: All


### tell

Synopsis: 
#include <io.h> 
long int tell( int handle ); 

Description: The tell function determines the current file position at the operating system level.  The handle value is the file handle returned by a successful execution of the  open function. 
The returned value may be used in conjunction with the  lseek function to reset the current file position. 

Returns: When an error occurs, -1 is returned.  When an error has occurred,  errno contains a value indicating the type of error that has been detected. 
Otherwise, the current file position is returned in a system-dependent manner.  A value of 0 indicates the start of the file. 

See Also: chsize, close, creat, dup, dup2, eof, exec Functions, filelength, fileno, fstat, isatty, lseek, open, read, setmode, sopen, stat, write, umask 

Example: 
#include <stdio.h> 
#include <sys\stat.h> 
#include <io.h> 
#include <fcntl.h> 
char buffer[] 
    = { "A text record to be written" }; 
void main() 
 { 
  int handle; 
  int size_written; 
  /* open a file for output       */ 
  /* replace existing file if it exists */ 
  handle = open( "file", 
        O_WRONLY | O_CREAT | O_TRUNC | O_TEXT, 
        S_IRUSR | S_IWUSR | S_IRGRP | S_IWGRP ); 
  if( handle != -1 ) { 
   /* print file position */ 
   printf( "%ld\n", tell( handle ) ); 
   /* write the text */ 
   size_written = write( handle, buffer, 
              sizeof( buffer ) ); 
   /* print file position */ 
   printf( "%ld\n", tell( handle ) ); 
   /* close the file */ 
   close( handle ); 
  } 
 } 
produces the following: 
0 
28 

Classification: WATCOM 

Systems: All


### time

Synopsis: 
#include <time.h> 
time_t time( time_t *tloc ); 

Description: The time function determines the current calendar time and encodes it into the type  time_t. 
The time represents the time since January 1, 1970 Coordinated Universal Time (UTC) (formerly known as Greenwich Mean Time (GMT)). 
The time set on the computer with the DOS time command and the DOS date command reflects the local time.  The environment variable TZ is used to establish the time zone to which this local time applies.  See the section The TZ Environment Variable for a discussion of how to set the time zone. 

Returns: The time function returns the current calendar time.  If tloc is not NULL, the current calendar time is also stored in the object pointed to by tloc. 

See Also: asctime, clock, ctime, difftime, gmtime, localtime, mktime, strftime, tzset 

Example: 
#include <stdio.h> 
#include <time.h> 
void main() 
 { 
  time_t time_of_day; 
  time_of_day = time( NULL ); 
  printf( "It is now: %s", ctime( &time_of_day ) ); 
 } 
produces the following: 
It is now: Fri Dec 25 15:58:42 1987 

Classification: ANSI, POSIX 1003.1 

Systems: All


### tmpfile

Synopsis: 
#include <stdio.h> 
FILE *tmpfile( void ); 

Description: The tmpfile function creates a temporary binary file that will automatically be removed when it is closed or at program termination.  The file is opened for update. 

Returns: The  tmpfile function returns a pointer to the stream of the file that it created.  If the file cannot be created, the  tmpfile function returns NULL.  When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

See Also: fopen, freopen, tmpnam 

Example: 
#include <stdio.h> 
static FILE *TempFile; 
void main() 
 { 
  TempFile = tmpfile(); 
  /* . */ 
  /* . */ 
  /* . */ 
  fclose( TempFile ); 
 } 

Classification: ANSI 

Systems: All


### tmpnam

Synopsis: 
#include <stdio.h> 
char *tmpnam( char *buffer ); 

Description: The  tmpnam function generates a unique string for use as a valid file name.  An internal static buffer is used to construct the filename.  Subsequent calls to tmpnam reuse the internal buffer. 

Returns: If the argument buffer is a NULL pointer, tmpnam returns a pointer to an internal buffer containing the temporary file name.  If the argument buffer is not a NULL pointer, tmpnam copies the temporary file name from the internal buffer to the specified buffer and returns a pointer to the specified buffer.  It is assumed that the specified buffer is an array of at least  L_tmpnam characters. 
If the argument buffer is a NULL pointer, you may wish to duplicate the resulting string since subsequent calls to tmpnam reuse the internal buffer. 
    
   char *name1, *name2; 
   name1 = strdup( tmpnam( NULL ) ); 
   name2 = strdup( tmpnam( NULL ) ); 

See Also: tmpfile 

Example: 
#include <stdio.h> 
void main() 
 { 
  char filename[ L_tmpnam ]; 
  FILE *fp; 
  tmpnam( filename ); 
  fp = fopen( filename, "w+b" ); 
  /* . */ 
  /* . */ 
  /* . */ 
  fclose( fp ); 
  remove( filename ); 
 } 

Classification: ANSI 

Systems: All


### tolower

Synopsis: 
#include <ctype.h> 
int tolower( int c ); 

Description: The tolower function converts an uppercase letter to the corresponding lowercase letter. 

Returns: The tolower function returns the corresponding lowercase letter when the argument is an uppercase letter; otherwise, the original character is returned. 

See Also: isalnum, isalpha, iscntrl, isdigit, isgraph, islower, isprint, ispunct, isspace, isupper, isxdigit, strlwr, strupr, toupper 

Example: 
#include <stdio.h> 
#include <ctype.h> 
char chars[] = { 
  'A', 
  '5', 
  '$', 
  'Z' 
}; 
#define SIZE sizeof( chars ) / sizeof( char ) 
void main() 
 { 
  int  i; 
  for( i = 0; i < SIZE; i++ ) { 
    printf( "%c ", tolower( chars[ i ] ) ); 
  } 
  printf( "\n" ); 
 } 
produces the following: 
a 5 $ z 

Classification: ANSI 

Systems: All


### toupper

Synopsis: 
#include <ctype.h> 
int toupper( int c ); 

Description: The toupper function converts a lowercase character to the corresponding uppercase character. 

Returns: The toupper function returns the corresponding uppercase letter when the argument is an lowercase letter; otherwise, the original character is returned. 

See Also: isalnum, isalpha, iscntrl, isdigit, isgraph, islower, isprint, ispunct, isspace, isupper, isxdigit, strlwr, strupr, tolower 

Example: 
#include <stdio.h> 
#include <ctype.h> 
char chars[] = { 
  'a', 
  '5', 
  '$', 
  'z' 
}; 
#define SIZE sizeof( chars ) / sizeof( char ) 
void main() 
 { 
  int  i; 
  for( i = 0; i < SIZE; i++ ) { 
    printf( "%c ", toupper( chars[ i ] ) ); 
  } 
  printf( "\n" ); 
 } 
produces the following: 
A 5 $ Z 

Classification: ANSI 

Systems: All


### tzset

Synopsis: 
#include <time.h> 
void tzset( void ); 

Description: The tzset function sets the global variables  daylight,  timezone and  tzname according to the value of the  TZ environment variable.  The section The TZ Environment Variable describes how to set this variable. 
Under Windows NT, tzset also uses operating system supplied time zone information.  The  TZ environment variable can be used to override this information. 
The global variables have the following values after tzset is executed: 

daylight Zero indicates that daylight saving time is not supported in the locale; a non-zero value indicates that daylight saving time is supported in the locale.  This variable is cleared/set after a call to the tzset function depending on whether a daylight saving time abbreviation is specified in the  TZ environment variable. 

timezone Contains the number of seconds that the local time zone is earlier than Coordinated Universal Time (UTC) (formerly known as Greenwich Mean Time (GMT)). 

tzname Two-element array pointing to strings giving the abbreviations for the name of the time zone when standard and daylight saving time are in effect. 
The time set on the computer with the DOS time command and the DOS date command reflects the local time. The environment variable TZ is used to establish the time zone to which this local time applies.  See the section The TZ Environment Variable for a discussion of how to set the time zone. 

Returns: The function does not return a value. 

See Also: ctime, localtime, mktime, strftime 

Example: 
#include <stdio.h> 
#include <env.h> 
#include <time.h> 
void print_zone() 
 { 
  char *tz; 
  printf( "TZ: %s\n", (tz = getenv( "TZ" )) 
          ? tz : "default EST5EDT" ); 
  printf( "  daylight: %d\n", daylight ); 
  printf( "  timezone: %ld\n", timezone ); 
  printf( "  time zone names: %s %s\n", 
      tzname[0], tzname[1] ); 
 } 
void main() 
 { 
  print_zone(); 
  setenv( "TZ", "PST8PDT", 1 ); 
  tzset(); 
  print_zone(); 
 } 
produces the following: 
TZ: default EST5EDT 
 daylight: 1 
 timezone: 18000 
 time zone names: EST EDT 
TZ: PST8PDT 
 daylight: 1 
 timezone: 28800 
 time zone names: PST PDT 

Classification: POSIX 1003.1 

Systems: All


### ultoa

Synopsis: 
#include <stdlib.h> 
char *ultoa( unsigned long int value, 
       char *buffer, 
       int radix ); 

Description: The ultoa function converts the unsigned binary integer value into the equivalent string in base radix notation storing the result in the character array pointed to by buffer.  A null character is appended to the result.  The size of buffer must be at least 33 bytes when converting values in base 2. 

Returns: The ultoa function returns the pointer to the result. 

See Also: atol, ltoa, strtol, strtoul, utoa 

Example: 
#include <stdio.h> 
#include <stdlib.h> 
void print_value( unsigned long int value ) 
 { 
  int base; 
  char buffer[18]; 
  for( base = 2; base <= 16; base = base + 2 ) 
   printf( "%2d %s\n", base, 
       ultoa( value, buffer, base ) ); 
 } 
void main() 
 { 
  print_value( (unsigned) 12765L ); 
 } 
produces the following: 
 2 11000111011101 
 4 3013131 
 6 135033 
 8 30735 
10 12765 
12 7479 
14 491b 
16 31dd 

Classification: WATCOM 

Systems: All


### umask

Synopsis: 
#include <sys\types.h> 
#include <sys\stat.h> 
#include <fcntl.h> 
#include <io.h> 
int umask( int cmask ); 

Description: The umask function sets the process's file mode creation mask to cmask.  The process's file mode creation mask is used during  creat,  open or  sopen to turn off permission bits in the permission argument supplied.  In other words, if a bit in the mask is on, then the corresponding bit in the file's requested permission value is disallowed. 
The argument cmask is a constant expression involving the constants described below.  The access permissions for the file or directory are specified as a combination of bits (defined in the <sys\stat.h> header file). 
The following bits define permissions for the owner. 

S_IRWXU Read, write, execute/search 

S_IRUSR Read permission 

S_IWUSR Write permission 

S_IXUSR Execute/search permission 
The following bits define permissions for the group. 

S_IRWXG Read, write, execute/search 

S_IRGRP Read permission 

S_IWGRP Write permission 

S_IXGRP Execute/search permission 
The following bits define permissions for others. 

S_IRWXO Read, write, execute/search 

S_IROTH Read permission 

S_IWOTH Write permission 

S_IXOTH Execute/search permission 
The following bits define miscellaneous permissions used by other implementations. 

S_IREAD is equivalent to S_IRUSR (read permission) 

S_IWRITE is equivalent to S_IWUSR (write permission) 

S_IEXEC is equivalent to S_IXUSR (execute/search permission) 
For example, if  S_IRUSR is specified, then reading is not allowed (i.e., the file is write only).  If  S_IWUSR is specified, then writing is not allowed (i.e., the file is read only). 

Returns: The umask function returns the previous value of cmask. 

See Also: chmod, creat, mkdir, open, sopen 

Example: 
#include <sys\types.h> 
#include <sys\stat.h> 
#include <fcntl.h> 
#include <io.h> 
void main() 
 { 
  int old_mask; 
  /* set mask to create read-only files */ 
  old_mask = umask( S_IWUSR | S_IWGRP | S_IWOTH | 
           S_IXUSR | S_IXGRP | S_IXOTH ); 
 } 

Classification: POSIX 1003.1 

Systems: All


### ungetc

Synopsis: 
#include <stdio.h> 
int ungetc( int c, FILE *fp ); 

Description: The  ungetc function pushes the character specified by c back onto the input stream pointed to by fp.  This character will be returned by the next read on the stream.  The pushed-back character will be discarded if a call is made to the  fflush function or to a file positioning function ( fseek,  fsetpos or  rewind) before the next read operation is performed. 
Only one character (the most recent one) of pushback is remembered. 
The  ungetc function clears the end-of-file indicator, unless the value of c is  EOF. 

Returns: The  ungetc function returns the character pushed back. 

See Also: fopen, getc 

Example: 
#include <stdio.h> 
#include <ctype.h> 
void main() 
 { 
  FILE *fp; 
  int c; 
  long value; 
  fp = fopen( "file", "r" ); 
  value = 0; 
  c = fgetc( fp ); 
  while( isdigit(c) ) { 
    value = value*10 + c - '0'; 
    c = fgetc( fp ); 
  } 
  ungetc( c, fp ); /* put last character back */ 
  printf( "Value=%ld\n", value ); 
  fclose( fp ); 
 } 

Classification: ANSI 

Systems: All


### ungetch

Synopsis: 
#include <conio.h> 
int ungetch( int c ); 

Description: The ungetch function pushes the character specified by c back onto the input stream for the console.  This character will be returned by the next read from the console (with  getch or  getche functions) and will be detected by the function  kbhit.  Only the last character returned in this way is remembered. 
The ungetch function clears the end-of-file indicator, unless the value of c is  EOF. 

Returns: The ungetch function returns the character pushed back. 

See Also: getch, getche, kbhit, putch 

Example: 
#include <stdio.h> 
#include <ctype.h> 
#include <conio.h> 
void main() 
 { 
  int c; 
  long value; 
  value = 0; 
  c = getche(); 
  while( isdigit( c ) ) { 
    value = value*10 + c - '0'; 
    c = getche(); 
  } 
  ungetch( c ); 
  printf( "Value=%ld\n", value ); 
 } 

Classification: WATCOM 

Systems: All


### unlink

Synopsis: 
#include <io.h> 
int unlink( const char *path ); 

Description: The unlink function deletes the file whose name is the string pointed to by path.  This function is equivalent to the  remove function. 

Returns: The unlink function returns zero if the operation succeeds, non-zero if it fails. 

See Also: chdir, chmod, close, getcwd, mkdir, open, remove, rename, rmdir, stat 

Example: 
#include <io.h> 
void main() 
 { 
  unlink( "vm.tmp" ); 
 } 

Classification: POSIX 1003.1 

Systems: All


### unlock

Synopsis: 
#include <io.h> 
int unlock( int handle, 
      unsigned long offset, 
      unsigned long nbytes ); 

Description: The unlock function unlocks nbytes amount of previously locked data in the file designated by handle starting at byte offset in the file.  This allows other processes to lock this region of the file. 
Multiple regions of a file can be locked, but no overlapping regions are allowed.  You cannot unlock multiple regions in the same call, even if the regions are contiguous.  All locked regions of a file should be unlocked before closing a file or exiting the program. 
With DOS, locking is supported by version 3.0 or later.  Note that SHARE.COM or SHARE.EXE must be installed. 

Returns: The unlock function returns zero if successful, and -1 when an error occurs.  When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

See Also: lock, locking, open, sopen 

Example: 
#include <stdio.h> 
#include <fcntl.h> 
#include <io.h> 
void main() 
 { 
  int handle; 
  char buffer[20]; 
  handle = open( "file", O_RDWR | O_TEXT ); 
  if( handle != -1 ) { 
   if( lock( handle, 0L, 20L ) ) { 
    printf( "Lock failed\n" ); 
   } else { 
    read( handle, buffer, 20 ); 
    /* update the buffer here */ 
    lseek( handle, 0L, SEEK_SET ); 
    write( handle, buffer, 20 ); 
    unlock( handle, 0L, 20L ); 
   } 
   close( handle ); 
  } 
 } 

Classification: WATCOM 

Systems: All


### _unregisterfonts

Synopsis: 
#include <graph.h> 
void _FAR _unregisterfonts( void ); 

Description: The _unregisterfonts function frees the memory previously allocated by the  _registerfonts function.  The currently selected font is also unloaded. 
Attempting to use the  _setfont function after calling _unregisterfonts will result in an error. 

Returns: The _unregisterfonts function does not return a value. 

See Also: _registerfonts, _setfont, _getfontinfo, _outgtext, _getgtextextent, _setgtextvector, _getgtextvector 

Example: 
#include <conio.h> 
#include <stdio.h> 
#include <graph.h> 
main() 
{ 
  int i, n; 
  char buf[ 10 ]; 
  _setvideomode( _VRES16COLOR ); 
  n = _registerfonts( "*.fon" ); 
  for( i = 0; i < n; ++i ) { 
    sprintf( buf, "n%d", i ); 
    _setfont( buf ); 
    _moveto( 100, 100 ); 
    _outgtext( "WATCOM Graphics" ); 
    getch(); 
    _clearscreen( _GCLEARSCREEN ); 
  } 
  _unregisterfonts(); 
  _setvideomode( _DEFAULTMODE ); 
} 

Classification: PC Graphics 

Systems: DOS, QNX


### utime

Synopsis: 
#include <sys\utime.h> 
int utime( const char *path, 
      const struct utimbuf *times ); 
struct utimbuf { 
  time_t  actime;   /* access time */ 
  time_t  modtime;  /* modification time */ 
}; 

Description: The utime function records the access and modification times for the file identified by path.  Write access to this file must be permitted for the time to be recorded. 
When the times argument is NULL, the current time is recorded.  Otherwise, the argument must point at an object whose type is  struct utimbuf.  The modification time is taken from the  modtime field in this structure. 

Returns: The utime function returns zero when the time was successfully recorded.  A value of -1 indicates an error occurred. 

Errors: When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

EACCES Search permission is denied for a component of path or the times argument is NULL and the effective user ID of the process does not match the owner of the file and write access is denied. 

EINVAL The date is before 1980 (DOS only). 

EMFILE There are too many open files. 

ENOENT The specified path does not exist or path is an empty string. 

Example: 
#include <stdio.h> 
#include <sys\utime.h> 
void main( int argc, char *argv[] ) 
 { 
  if( (utime( argv[1], NULL ) != 0) && (argc > 1) ) { 
    printf( "Unable to set time for %s\n", argv[1] ); 
  } 
 } 

Classification: POSIX 1003.1 

Systems: All


### utoa

Synopsis: 
#include <stdlib.h> 
char *utoa( unsigned int value, 
      char *buffer, 
      int radix ); 

Description: The utoa function converts the unsigned binary integer value into the equivalent string in base radix notation storing the result in the character array pointed to by buffer.  A null character is appended to the result.  The size of buffer must be at least (8 * sizeof(int) + 1) bytes when converting values in base 2.  That makes the size 17 bytes on 16-bit machines, and 33 bytes on 32-bit machines. 

Returns: The  utoa function returns the pointer to the result. 

See Also: atoi, itoa, strtol, strtoul 

Example: 
#include <stdio.h> 
#include <stdlib.h> 
void main() 
 { 
  int base; 
  char buffer[18]; 
  for( base = 2; base <= 16; base = base + 2 ) 
   printf( "%2d %s\n", base, 
       utoa( (unsigned) 12765, buffer, base ) ); 
 } 
produces the following: 
 2 11000111011101 
 4 3013131 
 6 135033 
 8 30735 
10 12765 
12 7479 
14 491b 
16 31dd 

Classification: WATCOM 

Systems: All


### va_arg

Synopsis: 
#include <stdarg.h> 
type va_arg( va_list param, type ); 

Description:  va_arg is a macro that can be used to obtain the next argument in a list of variable arguments.  It must be used with the associated macros  va_start and  va_end.  A sequence such as 
    
     va_list curr_arg; 
     type next_arg; 
     next_arg = va_arg( curr_arg, type ); 
causes next_arg to be assigned the value of the next variable argument.  The type is the type of the argument originally passed. 
The macro  va_start must be executed first in order to properly initialize the variable next_arg and the macro  va_end should be executed after all arguments have been obtained. 
The data item curr_arg is of type  va_list which contains the information to permit successive acquisitions of the arguments. 

Returns: The macro returns the value of the next variable argument, according to type passed as the second parameter. 

See Also: va_end, va_start, vfprintf, vprintf, vsprintf 

Example: 
#include <stdio.h> 
#include <stdarg.h> 
void test_fn( const char *msg, 
       const char *types, 
       ... ); 
void main() 
 { 
  printf( "VA...TEST\n" ); 
  test_fn( "PARAMETERS: 1, \"abc\", 546", 
       "isi", 1, "abc", 546 ); 
  test_fn( "PARAMETERS: \"def\", 789", 
       "si", "def", 789 ); 
 } 
static void test_fn( 
 const char *msg,  /* message to be printed   */ 
 const char *types, /* parameter types (i,s)   */ 
 ... )        /* variable arguments    */ 
 { 
  va_list argument; 
  int  arg_int; 
  char *arg_string; 
  const char *types_ptr; 
  types_ptr = types; 
  printf( "\n%s -- %s\n", msg, types ); 
  va_start( argument, types ); 
  while( *types_ptr != '\0' ) { 
   if (*types_ptr == 'i') { 
    arg_int = va_arg( argument, int ); 
    printf( "integer: %d\n", arg_int ); 
   } else if (*types_ptr == 's') { 
    arg_string = va_arg( argument, char * ); 
    printf( "string:  %s\n", arg_string ); 
   } 
   ++types_ptr; 
  } 
  va_end( argument ); 
 } 
produces the following: 
VA...TEST 
PARAMETERS: 1, "abc", 546 -- isi 
integer: 1 
string:  abc 
integer: 546 
PARAMETERS: "def", 789 -- si 
string:  def 
integer: 789 

Classification: ANSI 

Systems: MACRO


### va_end

Synopsis: 
#include <stdarg.h> 
void va_end( va_list param ); 

Description:  va_end is a macro used to complete the acquisition of arguments from a list of variable arguments.  It must be used with the associated macros  va_start and  va_arg.  See the description for  va_arg for complete documentation on these macros. 

Returns: The macro does not return a value. 

See Also: va_arg, va_start, vfprintf, vprintf, vsprintf 

Example: 
#include <stdio.h> 
#include <stdarg.h> 
#include <time.h> 
#define ESCAPE 27 
void tprintf( int row, int col, char *fmt, ... ) 
 { 
  auto va_list ap; 
  char *p1, *p2; 
  va_start( ap, fmt ); 
  p1 = va_arg( ap, char * ); 
  p2 = va_arg( ap, char * ); 
  printf( "%c[%2.2d;%2.2dH", ESCAPE, row, col ); 
  printf( fmt, p1, p2 ); 
  va_end( ap ); 
 } 
void main() 
 { 
  struct tm  time_of_day; 
  time_t   ltime; 
  auto char  buf[26]; 
  time( &ltime ); 
  _localtime( &ltime, &time_of_day ); 
  tprintf( 12, 1, "Date and time is: %s\n", 
      _asctime( &time_of_day, buf ) ); 
 } 

Classification: ANSI 

Systems: MACRO


### va_start

Synopsis: 
#include <stdarg.h> 
void va_start( va_list param, previous ); 

Description:  va_start is a macro used to start the acquisition of arguments from a list of variable arguments.  The param argument is used by the  va_arg macro to locate the current acquired argument.  The previous argument is the argument that immediately precedes the "..." notation in the original function definition.  It must be used with the associated macros  va_arg and  va_end.  See the description of  va_arg for complete documentation on these macros. 

Returns: The macro does not return a value. 

See Also: va_arg, va_end, vfprintf, vprintf, vsprintf 

Example: 
#include <stdio.h> 
#include <stdarg.h> 
#include <time.h> 
#define ESCAPE 27 
void tprintf( int row, int col, char *fmt, ... ) 
 { 
  auto va_list ap; 
  char *p1, *p2; 
  va_start( ap, fmt ); 
  p1 = va_arg( ap, char * ); 
  p2 = va_arg( ap, char * ); 
  printf( "%c[%2.2d;%2.2dH", ESCAPE, row, col ); 
  printf( fmt, p1, p2 ); 
  va_end( ap ); 
 } 
void main() 
 { 
  struct tm  time_of_day; 
  time_t   ltime; 
  auto char  buf[26]; 
  time( &ltime ); 
  _localtime( &ltime, &time_of_day ); 
  tprintf( 12, 1, "Date and time is: %s\n", 
      _asctime( &time_of_day, buf ) ); 
 } 

Classification: ANSI 

Systems: MACRO


### _vbprintf

Synopsis: 
#include <stdio.h> 
#include <stdarg.h> 
int _vbprintf( char *buf, unsigned int bufsize, 
        const char *format, va_list arg ); 

Description: The _vbprintf function formats data under control of the format control string and writes the result to buf.  The argument bufsize specifies the size of the character array buf into which the generated output is placed.  The format string is described under the description of the  printf function.  The _vbprintf function is equivalent to the  _bprintf function, with the variable argument list replaced with arg, which has been initialized by the  va_start macro. 

Returns: The _vbprintf function returns the number of characters written, or a negative value if an output error occurred. 

See Also: _bprintf, cprintf, fprintf, printf, sprintf, va_arg, va_end, va_start, vcprintf, vfprintf, vprintf, vsprintf 

Example: 
The following shows the use of _vbprintf in a general error message routine. 
#include <stdio.h> 
#include <stdarg.h> 
#include <string.h> 
char msgbuf[80]; 
char *fmtmsg( char *format, ... ) 
 { 
  va_list arglist; 
  va_start( arglist, format ); 
  strcpy( msgbuf, "Error: " ); 
  _vbprintf( &msgbuf[7], 73, format, arglist ); 
  va_end( arglist ); 
  return( msgbuf ); 
 } 
void main() 
 { 
  char *msg; 
  msg = fmtmsg( "%s %d %s", "Failed", 100, "times" ); 
  printf( "%s\n", msg ); 
 } 

Classification: WATCOM 

Systems: All


### vcprintf

Synopsis: 
#include <conio.h> 
#include <stdarg.h> 
int vcprintf( const char *format, va_list arg ); 

Description: The vcprintf function writes output directly to the console under control of the argument format.  The  putch function is used to output characters to the console.  The format string is described under the description of the  printf function.  The vcprintf function is equivalent to the  cprintf function, with the variable argument list replaced with arg, which has been initialized by the  va_start macro. 

Returns: The vcprintf function returns the number of characters written, or a negative value if an output error occurred.  When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

See Also: _bprintf, cprintf, fprintf, printf, sprintf, va_arg, va_end, va_start, _vbprintf, vfprintf, vprintf, vsprintf 

Example: 
#include <conio.h> 
#include <stdarg.h> 
#include <time.h> 
#define ESCAPE 27 
void tprintf( int row, int col, char *format, ... ) 
 { 
  auto va_list arglist; 
  cprintf( "%c[%2.2d;%2.2dH", ESCAPE, row, col ); 
  va_start( arglist, format ); 
  vcprintf( format, arglist ); 
  va_end( arglist ); 
 } 
void main() 
 { 
  struct tm  time_of_day; 
  time_t   ltime; 
  auto char  buf[26]; 
  time( &ltime ); 
  _localtime( &ltime, &time_of_day ); 
  tprintf( 12, 1, "Date and time is: %s\n", 
      _asctime( &time_of_day, buf ) ); 
 } 

Classification: WATCOM 

Systems: All


### vcscanf

Synopsis: 
#include <conio.h> 
#include <stdarg.h> 
int vcscanf( const char *format, va_list args ) 

Description: The vcscanf function scans input from the console under control of the argument format.  The vcscanf function uses the function  getche to read characters from the console.  The format string is described under the description of the  scanf function. 
The vcscanf function is equivalent to the  cscanf function, with a variable argument list replaced with arg, which has been initialized using the  va_start macro. 

Returns: The vcscanf function returns  EOF when the scanning is terminated by reaching the end of the input stream.  Otherwise, the number of input arguments for which values were successfully scanned and stored is returned.  When a file input error occurs, the  errno global variable may be set. 

See Also: cscanf, fscanf, scanf, sscanf, va_arg, va_end, va_start, vfscanf, vscanf, vsscanf 

Example: 
#include <conio.h> 
#include <stdarg.h> 
void cfind( char *format, ... ) 
 { 
  va_list arglist; 
  va_start( arglist, format ); 
  vcscanf( format, arglist ); 
  va_end( arglist ); 
 } 
void main() 
 { 
  int day, year; 
  char weekday[10], month[12]; 
  cfind( "%s %s %d %d", 
      weekday, month, &day, &year ); 
  cprintf( "\n%s, %s %d, %d\n", 
      weekday, month, day, year ); 
 } 

Classification: WATCOM 

Systems: All


### vfprintf

Synopsis: 
#include <stdio.h> 
#include <stdarg.h> 
int vfprintf( FILE *fp, 
       const char *format, 
       va_list arg ); 

Description: The vfprintf function writes output to the file pointed to by fp under control of the argument format.  The format string is described under the description of the  printf function.  The vfprintf function is equivalent to the  fprintf function, with the variable argument list replaced with arg, which has been initialized by the  va_start macro. 

Returns: The vfprintf function returns the number of characters written, or a negative value if an output error occurred.  When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

See Also: _bprintf, cprintf, fprintf, printf, sprintf, va_arg, va_end, va_start, _vbprintf, vcprintf, vprintf, vsprintf 

Example: 
#include <stdio.h> 
#include <stdarg.h> 
FILE *LogFile; 
/* a general error routine */ 
void errmsg( char *format, ... ) 
 { 
  va_list arglist; 
  fprintf( stderr, "Error: " ); 
  va_start( arglist, format ); 
  vfprintf( stderr, format, arglist ); 
  va_end( arglist ); 
  if( LogFile != NULL ) { 
   fprintf( LogFile, "Error: " ); 
   va_start( arglist, format ); 
   vfprintf( LogFile, format, arglist ); 
   va_end( arglist ); 
  } 
 } 
void main() 
 { 
  LogFile = fopen( "error.log", "w" ); 
  errmsg( "%s %d %s", "Failed", 100, "times" ); 
 } 

Classification: ANSI 

Systems: All


### vfscanf

Synopsis: 
#include <stdio.h> 
#include <stdarg.h> 
int vfscanf( FILE *fp, 
       const char *format, 
       va_list arg ); 

Description: The vfscanf function scans input from the file designated by fp under control of the argument format.  The format string is described under the description of the  scanf function. 
The vfscanf function is equivalent to the  fscanf function, with a variable argument list replaced with arg, which has been initialized using the  va_start macro. 

Returns: The vfscanf function returns  EOF when the scanning is terminated by reaching the end of the input stream.  Otherwise, the number of input arguments for which values were successfully scanned and stored is returned.  When a file input error occurs, the  errno global variable may be set. 

See Also: cscanf, fscanf, scanf, sscanf, va_arg, va_end, va_start, vcscanf, vscanf, vsscanf 

Example: 
#include <stdio.h> 
#include <stdarg.h> 
void ffind( FILE *fp, char *format, ... ) 
 { 
  va_list arglist; 
  va_start( arglist, format ); 
  vfscanf( fp, format, arglist ); 
  va_end( arglist ); 
 } 
void main() 
 { 
  int day, year; 
  char weekday[10], month[12]; 
  ffind( stdin, 
      "%s %s %d %d", 
      weekday, month, &day, &year ); 
  printf( "\n%s, %s %d, %d\n", 
      weekday, month, day, year ); 
 } 

Classification: WATCOM 

Systems: All


### vprintf

Synopsis: 
#include <stdio.h> 
#include <stdarg.h> 
int vprintf( const char *format, va_list arg ); 

Description: The vprintf function writes output to the file  stdout under control of the argument format.  The format string is described under the description of the  printf function.  The vprintf function is equivalent to the  printf function, with the variable argument list replaced with arg, which has been initialized by the  va_start macro. 

Returns: The vprintf function returns the number of characters written, or a negative value if an output error occurred.  When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

See Also: _bprintf, cprintf, fprintf, printf, sprintf, va_arg, va_end, va_start, _vbprintf, vcprintf, vfprintf, vsprintf 

Example: 
The following shows the use of vprintf in a general error message routine. 
#include <stdio.h> 
#include <stdarg.h> 
void errmsg( char *format, ... ) 
 { 
  va_list arglist; 
  printf( "Error: " ); 
  va_start( arglist, format ); 
  vprintf( format, arglist ); 
  va_end( arglist ); 
 } 
void main() 
 { 
  errmsg( "%s %d %s", "Failed", 100, "times" ); 
 } 

Classification: ANSI 

Systems: All


### vscanf

Synopsis: 
#include <stdio.h> 
#include <stdarg.h> 
int vscanf( const char *format, 
      va_list arg ); 

Description: The vscanf function scans input from the file designated by stdin under control of the argument format.  The format string is described under the description of the  scanf function. 
The vscanf function is equivalent to the  scanf function, with a variable argument list replaced with arg, which has been initialized using the  va_start macro. 

Returns: The vscanf function returns  EOF when the scanning is terminated by reaching the end of the input stream.  Otherwise, the number of input arguments for which values were successfully scanned and stored is returned. 

See Also: cscanf, fscanf, scanf, sscanf, va_arg, va_end, va_start, vcscanf, vfscanf, vsscanf 

Example: 
#include <stdio.h> 
#include <stdarg.h> 
void find( char *format, ... ) 
 { 
  va_list arglist; 
  va_start( arglist, format ); 
  vscanf( format, arglist ); 
  va_end( arglist ); 
 } 
void main() 
 { 
  int day, year; 
  char weekday[10], month[12]; 
  find( "%s %s %d %d", 
      weekday, month, &day, &year ); 
  printf( "\n%s, %s %d, %d\n", 
      weekday, month, day, year ); 
 } 

Classification: WATCOM 

Systems: All


### vsprintf

Synopsis: 
#include <stdio.h> 
#include <stdarg.h> 
int vsprintf( char *buf, 
       const char *format, 
       va_list arg ); 

Description: The vsprintf function formats data under control of the format control string and writes the result to buf.  The format string is described under the description of the  printf function.  The vsprintf function is equivalent to the  sprintf function, with the variable argument list replaced with arg, which has been initialized by the  va_start macro. 

Returns: The vsprintf function returns the number of characters written, or a negative value if an output error occurred. 

See Also: _bprintf, cprintf, fprintf, printf, sprintf, va_arg, va_end, va_start, _vbprintf, vcprintf, vfprintf, vprintf 

Example: 
The following shows the use of vsprintf in a general error message routine. 
#include <stdio.h> 
#include <stdarg.h> 
#include <string.h> 
char msgbuf[80]; 
char *fmtmsg( char *format, ... ) 
 { 
  va_list arglist; 
  va_start( arglist, format ); 
  strcpy( msgbuf, "Error: " ); 
  vsprintf( &msgbuf[7], format, arglist ); 
  va_end( arglist ); 
  return( msgbuf ); 
 } 
void main() 
 { 
  char *msg; 
  msg = fmtmsg( "%s %d %s", "Failed", 100, "times" ); 
  printf( "%s\n", msg ); 
 } 

Classification: ANSI 

Systems: All


### vsscanf

Synopsis: 
#include <stdio.h> 
#include <stdarg.h> 
int vsscanf( const char *in_string, 
       const char *format, 
       va_list arg ); 

Description: The vsscanf function scans input from the string designated by in_string under control of the argument format.  The format string is described under the description of the  scanf function. 
The vsscanf function is equivalent to the  sscanf function, with a variable argument list replaced with arg, which has been initialized using the  va_start macro. 

Returns: The vsscanf function returns  EOF when the scanning is terminated by reaching the end of the input string.  Otherwise, the number of input arguments for which values were successfully scanned and stored is returned. 

See Also: cscanf, fscanf, scanf, sscanf, va_arg, va_end, va_start, vcscanf, vfscanf, vscanf 

Example: 
#include <stdio.h> 
#include <stdarg.h> 
void sfind( char *string, char *format, ... ) 
 { 
  va_list arglist; 
  va_start( arglist, format ); 
  vsscanf( string, format, arglist ); 
  va_end( arglist ); 
 } 
void main() 
 { 
  int day, year; 
  char weekday[10], month[12]; 
  sfind( "Saturday April 18 1987", 
      "%s %s %d %d", 
      weekday, month, &day, &year ); 
  printf( "\n%s, %s %d, %d\n", 
      weekday, month, day, year ); 
 } 

Classification: WATCOM 

Systems: All


### wait

Synopsis: 
#include <process.h> 
int wait( int *status ); 

Description: The wait function suspends the calling process until any of the caller's immediate child processes terminate. 
If status is not NULL, it points to a word that will be filled in with the termination status word and return code of the terminated child process. 
If the child process terminated normally, then the low order byte of the status word will be set to 0, and the high order byte will contain the low order byte of the return code that the child process passed to the  DOSEXIT function.  The  DOSEXIT function is called whenever  main returns, or  exit or  _exit are explicity called. 
If the child process did not terminate normally, then the high order byte of the status word will be set to 0, and the low order byte will contain one of the following values: 

1 Hard-error abort 

2 Trap operation 

3 SIGTERM signal not intercepted 

Returns: The wait function returns the child's process id if the child process terminated normally.  Otherwise, wait returns -1 and sets  errno to one of the following values: 

ECHILD No child processes exist for the calling process. 

EINTR The child process terminated abnormally. 

See Also: cwait, exit, _exit, spawn Functions 

Example: 
#include <stdlib.h> 
#include <process.h> 
void main() 
 { 
   int  process_id, status; 
   process_id = spawnl( P_NOWAIT, "child.exe", 
        "child", "parm", NULL ); 
   wait( &status ); 
 } 

Classification: OS/2 

Systems: QNX, OS/2 1.x(all), OS/2 2.x, NT


### wcstombs

Synopsis: 
#include <stdlib.h> 
size_t wcstombs( char *s, const wchar_t *pwcs, size_t n ); 

Description: The wcstombs function converts a sequence of wide character codes from the array pointed to by pwcs into a sequence of multibyte characters and stores them in the array pointed to by s.  The wcstombs function stops if a multibyte character would exceed the limit of n total bytes, or if the null character is stored.  At most n bytes of the array pointed to by s will be modified. 

Returns: If an invalid multibyte character is encountered, the wcstombs function returns (size_t)-1.  Otherwise, the wcstombs function returns the number of array elements modified, not including the terminating zero code if present. 

See Also: mblen, mbtowc, mbstowcs, wctomb 

Example: 
#include <stdio.h> 
#include <stdlib.h> 
wchar_t wbuffer[] = { 
  0x0073, 
  0x0074, 
  0x0072, 
  0x0069, 
  0x006e, 
  0x0067, 
  0x0000 
 }; 
void main() 
 { 
  char   mbsbuffer[50]; 
  int   i, len; 
  len = wcstombs( mbsbuffer, wbuffer, 50 ); 
  if( len != -1 ) { 
   for( i = 0; i < len; i++ ) 
    printf( "/%4.4x", wbuffer[i] ); 
   printf( "\n" ); 
   mbsbuffer[len] = '\0'; 
   printf( "%s(%d)\n", mbsbuffer, len ); 
  } 
 } 
produces the following: 
/0073/0074/0072/0069/006e/0067 
string(6) 

Classification: ANSI 

Systems: All


### wctomb

Synopsis: 
#include <stdlib.h> 
int wctomb( char *s, wchar_t wchar ); 

Description: The wctomb function determines the number of bytes required to represent the multibyte character corresponding to the code contained in wchar.  If s is not a NULL pointer, the multibyte character representation is stored in the array pointed to by s.  At most  MB_CUR_MAX characters will be stored. 

Returns: If s is a NULL pointer, the wctomb function returns zero if multibyte character encodings do not have state-dependent encoding, and non-zero otherwise.  If s is not a NULL pointer, the wctomb function returns: 

-1 if the value of wchar does not correspond to a valid multibyte character 

len the number of bytes that comprise the multibyte character corresponding to the value of wchar. 

See Also: mblen, mbstowcs, mbtowc, wcstombs 

Example: 
#include <stdio.h> 
#include <stdlib.h> 
wchar_t wchar = { 0x0073 }; 
char   mbbuffer[MB_CUR_MAX]; 
void main() 
 { 
  int len; 
  printf( "Character encodings do %shave " 
      "state-dependent encoding\n", 
      ( wctomb( NULL, 0 ) ) 
      ? "" : "not " ); 
  len = wctomb( mbbuffer, wchar ); 
  mbbuffer[len] = '\0'; 
  printf( "%s(%d)\n", mbbuffer, len ); 
 } 
produces the following: 
Character encodings do not have state-dependent encoding 
s(1) 

Classification: ANSI 

Systems: All


### _wrapon

Synopsis: 
#include <graph.h> 
short _FAR _wrapon( short wrap ); 

Description: The _wrapon function is used to control the display of text when the text output reaches the right side of the text window.  This is text displayed with the  _outtext and  _outmem functions.  The wrap argument can take one of the following values: 

_GWRAPON causes lines to wrap at the window border 

_GWRAPOFF causes lines to be truncated at the window border 

Returns: The _wrapon function returns the previous setting for wrapping. 

See Also: _outtext, _outmem, _settextwindow 

Example: 
#include <conio.h> 
#include <graph.h> 
#include <stdio.h> 
main() 
{ 
  int i; 
  char buf[ 80 ]; 
  _setvideomode( _TEXTC80 ); 
  _settextwindow( 5, 20, 20, 30 ); 
  _wrapon( _GWRAPOFF ); 
  for( i = 1; i <= 3; ++i ) { 
    _settextposition( 2 * i, 1 ); 
    sprintf( buf, "Very very long line %d", i ); 
    _outtext( buf ); 
  } 
  _wrapon( _GWRAPON ); 
  for( i = 4; i <= 6; ++i ) { 
    _settextposition( 2 * i, 1 ); 
    sprintf( buf, "Very very long line %d", i ); 
    _outtext( buf ); 
  } 
  getch(); 
  _setvideomode( _DEFAULTMODE ); 
} 

Classification: PC Graphics 

Systems: DOS, QNX


### write

Synopsis: 
#include <io.h> 
int write( int handle, void *buffer, unsigned len ); 

Description: The write function writes data at the operating system level.  The number of bytes transmitted is given by len and the data to be transmitted is located at the address specified by buffer. 
The handle value is returned by the  open function.  The access mode must have included either O_WRONLY or O_RDWR when the  open function was invoked. 
The data is written to the file at the end when the file was opened with O_APPEND included as part of the access mode; otherwise, it is written at the current file position for the file in question.  This file position can be determined with the  tell function and can be set with the  lseek function. 
When O_BINARY is included in the access mode, the data is transmitted unchanged.  When O_TEXT is included in the access mode, the data is transmitted with extra carriage return characters inserted before each linefeed character encountered in the original data. 
A file can be truncated under DOS and OS/2 2.0 by specifying 0 as the len argument.  Note, however, that this doesn't work under OS/2 2.1, Windows NT, and other operating systems.  To truncate a file in a portable manner, use the  chsize function. 

Returns: The write function returns the number of bytes (does not include any extra carriage-return characters transmitted) of data transmitted to the file.  When there is no error, this is the number given by the len argument.  In the case of an error, such as there being no space available to contain the file data, the return value will be less than the number of bytes transmitted.  A value of -1 may be returned in the case of some output errors.  When an error has occurred,  errno contains a value indicating the type of error that has been detected. 

See Also: chsize, close, creat, dup, dup2, eof, exec Functions, filelength, fileno, fstat, isatty, lseek, open, read, setmode, sopen, stat, tell, umask 

Example: 
#include <stdio.h> 
#include <io.h> 
#include <fcntl.h> 
char buffer[] 
    = { "A text record to be written" }; 
void main() 
 { 
  int handle; 
  int size_written; 
  /* open a file for output       */ 
  /* replace existing file if it exists */ 
  handle = open( "file", 
        O_WRONLY | O_CREAT | O_TRUNC | O_TEXT, 
        S_IRUSR | S_IWUSR | S_IRGRP | S_IWGRP ); 
  if( handle != -1 ) { 
   /* write the text           */ 
   size_written = write( handle, buffer, 
              sizeof( buffer ) ); 
   /* test for error           */ 
   if( size_written != sizeof( buffer ) ) { 
     printf( "Error writing file\n" ); 
   } 
   /* close the file           */ 
   close( handle ); 
  } 
 } 

Classification: POSIX 1003.1 

Systems: All


## Re-entrant Functions

The following functions in the C library are re-entrant: 
    
   abs      atoi     atol     bsearch 
   div      fabs     _fmemccpy   _fmemchr 
   _fmemcmp   _fmemcpy   _fmemicmp   _fmemmove 
   _fmemset   _fstrcat   _fstrchr   _fstrcmp 
   _fstrcpy   _fstrcspn   _fstricmp   _fstrlen 
   _fstrlwr   _fstrncat   _fstrncmp   _fstrncpy 
   _fstrnicmp  _fstrnset   _fstrpbrk   _fstrrchr 
   _fstrrev   _fstrset   _fstrspn   _fstrstr 
   _fstrupr   isalnum    isalpha    isascii 
   iscntrl    isdigit    isgraph    islower 
   isprint    ispunct    isspace    isupper 
   isxdigit   itoa     labs     ldiv 
   lfind     longjmp    _lrotl    _lrotr 
   lsearch    ltoa     _makepath   mblen 
   mbstowcs   mbtowc    memccpy    memchr 
   memcmp    memcpy    memicmp    memmove 
   memset    movedata   qsort     _rotl 
   _rotr     segread    setjmp    _splitpath 
   strcat    strchr    strcmp    strcoll 
   strcpy    strcspn    stricmp    strlen 
   strlwr    strncat    strncmp    strncpy 
   strnicmp   strnset    strpbrk    strrchr 
   strrev    strset    strspn    strstr 
   strupr    swab     tolower    toupper 
   ultoa     utoa     wcstombs   wctomb


## Implementation-Defined Behavior

This appendix describes the behavior of WATCOM C and WATCOM C/386 libraries when the ANSI C Language standard describes the behavior as implementation-defined.  The term describing each behavior is taken directly from the ANSI C Language standard.  The numbers in parentheses at the end of each term refers to the section of the standard that discusses the behavior.


### Library Functions


#### NULL Macro

The null pointer constant to which the macro  NULL expands (4.1.5). 
The macro  NULL expands to 0 in small data models and to 0L in large data models.


#### Diagnostic Printed by the assert Function

The diagnostic printed by and the termination behavior of the  assert function (4.2). 
The  assert function prints a diagnostic message to  stderr and calls the  abort routine if the expression is false.  The diagnostic message has the following form: 
    
   Assertion failed: [expression], file [name], line [number]


#### Character Testing

The sets of characters tested for by the  isalnum,  isalpha,  iscntrl,  islower,  isprint, and  isupper functions (4.3.1). 

isalnum Characters 0-9, A-Z, a-z 

isalpha Characters A-Z, a-z 

iscntrl ASCII 0x00-0x1f, 0x7f 

islower Characters a-z 

isprint ASCII 0x20-0x7e 

isupper Characters A-Z


#### Domain Errors

The values returned by the mathematics functions on domain errors (4.5.1). 
When a domain error occurs, the listed values are returned by the following functions: 

acos 0.0 

acosh - HUGE_VAL 

asin 0.0 

atan2 0.0 

atanh - HUGE_VAL 

log - HUGE_VAL 

log10 - HUGE_VAL 

log2 - HUGE_VAL 

pow(neg,frac) 0.0 

pow(0.0,0.0) 1.0 

pow(0.0,neg) - HUGE_VAL 

sqrt 0.0 

y0 - HUGE_VAL 

y1 - HUGE_VAL 

yn - HUGE_VAL


#### Underflow of Floating-Point Values

Whether the mathematics functions set the integer expression  errno to the value of the macro  ERANGE on underflow range errors (4.5.1). 
The integer expression  errno is not set to  ERANGE on underflow range errors in the mathematics functions.


#### The fmod Function

Whether a domain error occurs or zero is returned when the  fmod function has a second argument of zero (4.5.6.4). 
Zero is returned when the second argument to  fmod is zero.


#### The signal Function

The set of signals for the  signal function (4.7.1.1). 
See the description of the  signal function presented earlier in this book. 
The semantics for each signal recognized by the  signal function (4.7.1.1). 
See the description of the  signal function presented earlier in this book. 
The default handling and the handling at program startup for each signal recognized by the  signal function (4.7.1.1). 
See the description of the  signal function presented earlier in this book.


#### Default Signals

If the equivalent of  signal( sig, SIG_DFL ) is not executed prior to the call of a signal handler, the blocking of the signal that is performed (4.7.1.1). 
The equivalent of 
    
   signal( sig, SIG_DFL ); 
is executed prior to the call of a signal handler.


#### The SIGILL Signal

Whether the default handling is reset if the  SIGILL signal is received by a handler specified to the  signal function (4.7.1.1). 
The equivalent of 
    
   signal( SIGILL, SIG_DFL ); 
is executed prior to the call of the signal handler.


#### Terminating Newline Characters

Whether the last line of a text stream requires a terminating new-line character (4.9.2). 
The last line of a text stream does not require a terminating new-line character.


#### Space Characters

Whether space characters that are written out to a text stream immediately before a new-line character appear when read in (4.9.2). 
All characters written out to a text stream will appear when read in.


#### Null Characters

The number of null characters that may be appended to data written to a binary stream (4.9.2). 
No null characters are appended to data written to a binary stream.


#### File Position in Append Mode

Whether the file position indicator of an append mode stream is initially positioned at the beginning or end of the file (4.9.3). 
When a file is open in append mode, the file position indicator initially points to the end of the file.


#### Truncation of Text Files

Whether a write on a text stream causes the associated file to be truncated beyond that point (4.9.3). 
Writing to a text stream does not truncate the file beyond that point.


#### File Buffering

The characteristics of file buffering (4.9.3). 
Disk files accessed through the standard I/O functions are fully buffered.  The default buffer size is 512 bytes for 16-bit systems, and 4096 bytes for 32-bit systems.


#### Zero-Length Files

Whether a zero-length file actually exists (4.9.3). 
A file with length zero can exist.


#### File Names

The rules of composing valid file names (4.9.3). 
A valid file specification consists of an optional drive letter (which is always followed by a colon), a series of optional directory names separated by backslashes, and a file name. 
Directory names and file names can contain up to eight characters followed optionally by a period and a three letter extension.  Case is ignored.


#### File Access Limits

Whether the same file can be open multiple times (4.9.3). 
It is possible to open a file multiple times.


#### Deleting Open Files

The effect of the  remove function on an open file (4.9.4.1). 
The  remove function deletes a file, even if the file is open.


#### Renaming with a Name that Exists

The effect if a file with the new name exists prior to a call to the  rename function (4.9.4.2). 
The  rename function will fail if you attempt to rename a file using a name that exists.


#### Printing Pointer Values

The output for %p conversion in the  fprintf function (4.9.6.1). 
Two types of pointers are supported:  near pointers (%hp), and far pointers (%lp).  The output for %p depends on the memory model being used. 
In 16-bit mode, the  fprintf function produces hexadecimal values of the form XXXX for 16-bit near pointers, and XXXX:XXXX (segment and offset separated by a colon) for 32-bit far pointers. 
In 32-bit mode, the  fprintf function produces hexadecimal values of the form XXXXXXXX for 32-bit near pointers, and XXXX:XXXXXXXX (segment and offset separated by a colon) for 48-bit far pointers.


#### Reading Pointer Values

The input for %p conversion in the  fscanf function (4.9.6.2). 
The  fscanf function converts hexadecimal values into the correct address when the %p format specifier is used.


#### Reading Ranges

The interpretation of a - character that is neither the first nor the last character in the scanlist for %[ conversion in the  fscanf function (4.9.6.2). 
The "-" character indicates a character range.  The character prior to the "-" is the first character in the range.  The character following the "-" is the last character in the range.


#### File Position Errors

The value to which the macro  errno is set by the  fgetpos or  ftell function on failure (4.9.9.1, 4.9.9.4). 
When the function  fgetpos or  ftell fails, they set  errno to  EBADF if the file number is bad.  The constants are defined in the <errno.h> header file.


#### Messages Generated by the perror Function

The messages generated by the  perror function (4.9.10.4). 
The  perror function generates the following messages. 

0 "Error 0" 

1 "No such file or directory" 

2 "Argument list too big" 

3 "Exec format error" 

4 "Bad file number" 

5 "Not enough memory" 

6 "Permission denied" 

7 "File exists" 

8 "Cross-device link" 

9 "Invalid argument" 

10 "File table overflow" 

11 "Too many open files" 

12 "No space left on device" 

13 "Argument too large" 

14 "Result too large" 

15 "Resource deadlock would occur"


#### Allocating Zero Memory

The behavior of the  calloc,  malloc, or  realloc function if the size requested is zero (4.10.3). 
The value returned will be  NULL.  No actual memory is allocated.


#### The abort Function

The behavior of the  abort function with regard to open and temporary files (4.10.4.1). 
The  abort function does not close any files that are open or temporary, nor does it flush any output buffers.


#### The atexit Function

The status returned by the  exit function if the value of the argument is other than zero,  EXIT_SUCCESS, or  EXIT_FAILURE (4.10.4.3). 
The  exit function returns the value of its argument to the operating system regardless of its value.


#### Environment Names

The set of environment names and the method for altering the environment list used by the  getenv function (4.10.4.4). 
The set of environment names is unlimited.  Environment variables can be set from the DOS command line using the SET command.  A program can modify its environment variables with the  putenv function.  Such modifications last only until the program terminates.


#### The system Function

The contents and mode of execution of the string by the  system function (4.10.4.5). 
The  system function executes an internal DOS or OS/2 command, or an EXE, COM, or BAT file from within a C program rather than from the command line.  The  system function examines the  COMSPEC environment variable to find the command interpreter and passes the argument string to the command interpreter.


#### The strerror Function

The contents of the error message strings returned by the  strerror function (4.11.6.2). 
The  strerror function generates the following messages. 

0 "Error 0" 

1 "No such file or directory" 

2 "Argument list too big" 

3 "Exec format error" 

4 "Bad file number" 

5 "Not enough memory" 

6 "Permission denied" 

7 "File exists" 

8 "Cross-device link" 

9 "Invalid argument" 

10 "File table overflow" 

11 "Too many open files" 

12 "No space left on device" 

13 "Argument too large" 

14 "Result too large" 

15 "Resource deadlock would occur"


#### The Time Zone

The local time zone and Daylight Saving Time (4.12.1). 
The default time zone is "Eastern Standard Time" (EST), and the corresponding daylight saving time zone is "Eastern Daylight Saving Time" (EDT).


#### The clock Function

The era for the  clock function (4.12.2.1). 
The  clock function's era begins with a value of 0 when the program starts to execute.
