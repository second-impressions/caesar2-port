# System Object Model (SOM) Reference


## How to Use the SOM Reference

The OS/2* 2.0 SOM Reference is a detailed technical reference for application programmers.  It gives reference information and code examples to enable you to write source code that uses SOM. 

Before you begin to use this information, it would be helpful to understand how you can: 

oExpand the Contents to see all available topics 
oObtain additional information for a highlighted word or phrase 
oUse action bar choices 
oUse the programming information. 

How to Use the Contents 

When the Contents window first appears, some topics have a plus (+) sign beside them. The plus sign indicates that additional topics are available. 

To expand the Contents if you are using a mouse, click on the plus sign.  If you are using the keyboard, use the Up or Down Arrow key to highlight the topic, and press the plus (+) key. For example, SOM Compiler has a plus sign beside it. To see additional topics for that heading, click on the plus sign or highlight that topic and press the plus (+) key. 

To view a topic, double-click on the topic (or press the Up or Down Arrow key to highlight the topic, and then press the Enter key). 

How to Obtain Additional Information 

After you select a topic, the information for that topic appears in a window.  Highlighted words or phrases indicate that additional information is available. You will notice that certain words and phrases are highlighted in green letters, or in white letters on a black background.  These are called hypertext terms. If you are using a mouse, double-click on the highlighted word.  If you are using a keyboard, press the Tab key to move to the highlighted word, and then press the Enter key.  Additional information then appears in a window. 

How to Use Action Bar Choices 

Several choices are available for managing information presented in the OS/2* 2.0 SOM Reference.  There are three pull-down menus on the action bar:  the Services menu, the Options menu, and the Help menu. 

The actions that are selectable from the Services menu operate on the active window currently displayed on the screen. These actions include the following: 

Bookmark Allows you to set a placeholder so you can retrieve information of interest to you. 

When you place a bookmark on a topic, it is added to a list of bookmarks you have previously set.  You can view the list, and you can remove one or all bookmarks from the list.  If you have not set any bookmarks, the list is empty. 

To set a bookmark, do the following: 

 1.Select a topic from the Contents. 

 2.When that topic appears, choose the Bookmark option from the Services pull-down. 

 3.If you want to change the name used for the bookmark, type the new name in the field. 

 4.Click on the Place radio button (or press the Up or Down Arrow key to select it). 

 5.Click on OK (or select it and press Enter). The bookmark is then added to the bookmark list. 

Search Allows you to find occurrences of a word or phrase in the current topic, selected topics, or all topics. 

You can specify a word or phrase to be searched.  You can also limit the search to a set of topics by first marking the topics in the Contents list. 

To search for a word or phrase in all topics, do the following: 

 1.Choose the Search option from the Services pull-down. 

 2.Type the word or words to be searched for. 

 3.Click on All sections (or press the Up or Down Arrow keys to select it). 

 4.Click on Search (or select it and press Enter) to begin the search. 

 5.The list of topics where the word or phrase appears is displayed. 

Print Allows you to print one or more topics.  You can also print a set of topics by first marking the topics in the Contents list. 

To print the document Contents list, do the following: 

 1.Choose Print from the Services pull-down. 

 2.Click on Contents (or press the Up or Down Arrow key to select it). 

 3.Click on Print (or select it and press Enter). 

 4.The Contents list is printed on your printer. 

Copy Allows you to copy a topic that you are viewing to the System Clipboard or to a file that you can edit. You will find this particularly useful for copying syntax definitions and program samples into the application that you are developing. 

You can copy a topic that you are viewing in two ways: 

oCopy copies the topic that you are viewing into the System Clipboard.  If you are using a Presentation Manager* (PM) editor (for example, the System Editor) that copies or cuts (or both) to the System Clipboard, and pastes to the System Clipboard, you can easily add the copied information to your program source module. 

oCopy to file copies the topic that you are viewing into a temporary file named TEXT.TMP.  You can later edit that file by using any editor.  You will find TEXT.TMP in the directory where your viewable document resides. 

To copy a topic, do the following: 

 1.Expand the Contents list and select a topic. 

 2.When the topic appears, choose Copy to file from the Services pull-down. 

 3.The system puts the text pertaining to that topic into the temporary file named TEXT.TMP. 

For information on one of the other choices in the Services pull-down, highlight the choice and press the F1 key. 

The actions that are selectable from the Options menu allow you to change the way your Contents list is displayed. To expand the Contents and show all levels for all topics, choose Expand all from the Options pull-down. You can also press the Ctrl and * keys together. For information on one of the other choices in the Options pull-down, highlight the choice and press the F1 key. 

The actions that are selectable from the Help menu allow you to select different types of help information.  You can also press the F1 key for help information about the Information Presentation Facility (IPF). 

How to Use the Programming Information 

The SOM Reference consists of reference information that provides a detailed description of each aspect of SOM. 

SOM programming information is presented by subject, such as Object Interface Definition Language, SOM Compiler, SOM Bindings for C, and Methods Reference, for example: 

```
     ┌─────────────────────────────────────────┐
     │            Contents                     │
     ├─────────────────────────────────────────┤
     │                                         │
     │  + Object Interface Definition Language │
     │  + SOM Compiler                         │
     │  + SOM Bindings for C                   │
     │  + Methods Reference                    │
     │                                         │
     └─────────────────────────────────────────┘
```

By clicking on the plus sign beside 'Methods Reference', you see an alphabetic list of the SOM methods. Selecting a method takes you directly into the reference information for that method. 

Units of reference information are presented in selectable multiple windows or viewports. A viewport is a Presentation Manager window that can be sized, moved, minimized, maximized, or closed.  By selecting a unit (in this case, an entry on the Contents list), you will see two windows displayed: 

```
    ┌──────────────┬─────────────────────────────┐
    │ Unit Title   │   Selection Title           │
    ├──────────────┼─────────────────────────────┤
    │ Topics:      │                             │
    │    .         │                             │
    │    .         │                             │
    │    .         │                             │
    │ Example      │                             │
    │ Error codes  │                             │
    │ Glossary     │                             │
    │              │                             │
    │              │                             │
    └──────────────┴─────────────────────────────┘
```

The window on the left is the primary window.  It contains a list of items that are always available to you.  The window on the right is the secondary window.  It contains a 'snapshot' of the unit information. For reference units (that is, method descriptions), this window contains the Call Syntax. 

All of the information needed to understand a method is readily available to you through the primary window. The information is divided into discrete information groups, and only the appropriate information group appears for the topic that you are viewing. 

The information groups for a method description can include the following: 

oCall Syntax 
oUses 
oParameters 
oError codes 
oReturn Values 
oNotes 
oRelated Methods 
oExample 
oGlossary 

This list may vary.  Uses, Notes, Related Methods, and Example may be omitted when they do not apply. 

Information groups are displayed in separate viewports that are usually stacked in a third window location that overlaps the secondary window. By selecting an item (information group) in the primary window, the item is displayed in the third window location: 

```
  ┌──────────────┬───────────────┬───────────────┐
  │ Unit Title   │   Selection Ti│   Parameters  │
  ├──────────────┼───────────────┼───────────────┤
  │ Topics:      │               │  receiver     │
  │              │               │    .          │
  │    .         │               │  classId      │
  │    .         │               │    .          │
  │    .         │               │    .          │
  │ Example      │               │    .          │
  │ Error codes  │               │    .          │
  │ Glossary     │               │               │
  │              │               │               │
  │              │               │               │
  └──────────────┴───────────────┴───────────────┘
```

By selecting successive items from the primary window, additional windows are displayed on top of the previous windows displayed in the third window location.  For example, in a method description, Uses and Parameters are items listed in the primary window.  When selected, they appear one on top of the other in the third window location. Because of this, you may move the first selected (topmost) window to the left before selecting the next item. This allows simultaneous display of two related pieces of information from the 'stack' of windows in the third window location: 

```
  ┌──────────────┬───────────────┬───────────────┐
  │ Unit Title   │   Parameters  │     Uses      │
  ├──────────────┼───────────────┼───────────────┤
  │ Topics:      │  receiver     │               │
  │              │    .          │    .          │
  │    .         │  classId      │    .          │
  │    .         │    .          │    .          │
  │    .         │    .          │    .          │
  │ Example      │    .          │    .          │
  │ Error codes  │    .          │    .          │
  │ Glossary     │               │               │
  │              │               │               │
  │              │               │               │
  └──────────────┴───────────────┴───────────────┘
```

Each window can be individually closed from its system menu.  All windows are closed when you close the primary window. 

Some secondary windows may have the appearance of a split screen. For example, an illustration may appear in the left half of the window, and scrollable, explanatory information may appear in the right half of the window.  Because illustrations may not necessarily fit into the small window size on your screen, you may maximize the secondary window for better readability.


## IBM Trademark *(hidden)*

Trademark of the IBM Corporation.


## Stepstone Trademark *(hidden)*

Objective-C is a trademark of the Stepstone Corporation.


## ANSI C Standard *(hidden)*

ANSI C refers to American National Standard X3.159-1989.


## Object Interface Definition Language

SOM Object Interface Definition Language (OIDL) files provide the basis for generating binding files that enable programming languages to use and provide SOM objects and their definitions (referred to as classes). Each OIDL file defines the complete interface to a class of SOM objects. 

OIDL files come in different forms for different languages. The different forms enable a class implementer to specify additional language-specific information that allows the SOM OIDL Compiler (or SOM Compiler, for short) to provide support for constructing the class. Each of these different forms shares a common core language that specifies the exact information that a user must know to use a class. One of the facilities of the SOM Compiler is the extraction of the common core part of a class definition. Thus, the class implementer can maintain a language-specific OIDL file for a class, and use the SOM Compiler to produce the language-neutral core definition as needed. 

This section describes OIDL with the extensions to support C-language programming. 

As indicated above, OIDL files are compiled by the SOM Compiler to produce a set of language-specific or use-specific binding files. The SOM Compiler will produce seven different files for the C language: 

oA public header file for programs that use a class. Use of a class includes creating instance objects of the class, calling methods on instance objects, and subclassing the class to produce new classes. 

oA private header file, which provides usage bindings to any private methods the class might have. 

oAn implementation header file, which provides macros and other material to support the implementation of the class. 

oAn implementation template, which provides an outline of the class' implementation that the class provider can then fill out. 

oA language-neutral core definition (as discussed above). 

oA private language-neutral core file, which contains private parts of the class' interface. 

oAn OS/2* .DEF file that can be used to package the class in the form of an OS/2* DLL. 

OIDL files can contain the following sections. Required sections are designated by (R); optional by (O): 

I. Include section (O) 
II. Class section (R) 
III. Release Order section (O) 
IV. Metaclass section (O) 
V. Parent Class section (R) 
VI. Passthru section (O) 
VII. Data section (O) 
VIII. Methods section (O) 

The SOM Compiler is somewhat flexible about the order of the sections, but the order listed above is highly recommended. The following describes the purpose and form of each of these sections. 

The discussion of each section begins with a brief description of its purpose followed by a section-specific syntax diagram. Syntax diagram constants appear in boldface (for example, #include, ,, =, ;, >, and "), while meta symbols appear in the standard font (for example, [...]). User-supplied elements appear in italics (for example, filename). 

Meta symbols have the following meanings: 

oParentheses (( )) indicate grouped parts of the syntax (for example, ( #include ...)). 

oSquare brackets ([ ]) indicate optional parts (for example, [, parent]). 

oAn asterisk (*) designates multiples from 0 or more (for example, [, name]*). 

oA plus sign (+) designates multiples from 1 or more (for example, [description3]+). 

oA vertical bar (|) indicates alternatives. Within a set of alternatives, an underscore will indicate the default if one is defined. (for example, global | local). 

Each syntax diagram is followed by a simple example. 

Finally, the parts of the section to be supplied by the user are individually described. Each user-input item is labeled "required" or "optional.". If designated "optional," its default will be given following the explanation.


### Include Section

This required section contains an include statement that is a directive to the OIDL preprocessor telling the compiler where to find the class interface definition for this class' parent class, the class' metaclass if the class specifies one, and the private interface files for any ancestor class for which this class overrides one or more of its private methods. 

Note:  The include statements must appear in the order shown below. In addition, the ancestor include statements must be in inheritance order (from the root down). 

The syntax for an include statement is: 

[#include ( <ancestor> | "ancestor" )]* 
#include ( <parent> | "parent" ) 
[#include ( <metaclass> | "metaclass" )] 

Example: 

```
#include "barfile.sc"
#include "foofile.sc"
#include <metafile.sc>
```

where: 

<ancestor> [optional] is the name of the OIDL file containing the private part of an ancestor class' interface needed in the definition of this class. If ancestor is enclosed in angle brackets (<>), the search for the file will begin in system-specific locations. If parent is enclosed in double quotation marks (""), the search for the file will begin in the local context, then move to the system-specific locations. 

<parent> [required] is the name of the OIDL file containing the parent class of the class for which the include statement is provided. If parent is enclosed in angle brackets (<>), the search for the file will begin in system-specific locations. If parent is enclosed in double quotation marks (""), the search for the file will begin in the local context, then move to the system-specific locations. 

<metaclass> [optional] is the OIDL file containing the metaclass of the class for which the include statement is provided. If metaclass is enclosed in angle brackets (<>), the search for the file will begin in system-specific locations. If metaclass is enclosed in double quotation marks (""), the search for the file will begin in the local context, then move to the system-specific locations. Refer to the note under Metaclass Section for additional information about when a metaclass include may be omitted.


### Class Section

This required section introduces the class, giving its name, attributes, and optionally a description of the class as a whole. 

The syntax for a class statement is: 

class: name 
    [, file stem = stem] 
    [, external stem = stem] 
    [, function prefix = prefix | 
     , external prefix = prefix] 
     , classprefix = prefix] 
    [, major version = number] 
    [, minor version = number] 
    [, global | local]; 
    [, classinit = function]; 
[description] 

Example: 

```
class: Foo,
       local,
       file stem = foofile,
       external prefix = xx_,
       major version = 1,
       minor version = 3;
-- This is the Foo class. It does nothing.
```

where: 

<name> [required] is the name for this class. 

file stem = stem [optional] is an attribute that specifies how the compiler is to construct file names for various generated files. The constructed file names will all begin with stem. 

Note:  This value is also used as the class library name in any generated .DEF file. 

This attribute defaults to the name of the file containing the class-interface definition. 

external stem = stem [optional] is an attribute that governs the formation of external names that appear in the text of the generated output files. On some systems, external names are limited in length to a small number of characters. The SOM Compiler uses the value stem as the basis for generating short external names. A suffix is appended to stem for each external name. Because OS/2* 2.0 external names may be up to 255 characters in length, short external names are generally not used. 

This attribute defaults to the same value given (or defaulted) by file stem. 

function prefix = prefix [optional] is an attribute that directs the compiler to construct method function names by prefixing method names with prefix. For example, function prefix = xx_ would result in a function name of xx_foo for a method called foo. 

Note:  It is an error to specify both function prefix and external prefix as attributes of the same class. 

This attribute has no default. 

external prefix = prefix [optional] is an attribute that is similar to function prefix except this attribute will also cause each method function to be an external name, whereas  method functions usually are local to the module in which they are defined. Making method functions external can be useful in development environments whose debuggers have difficulty dealing with local procedures. 

Note:  It is an error to specify both external prefix and function prefix as attributes of the same class. 

This attribute has no default. 

classprefix = prefix [optional] is similar to the function prefix attribute, but applies only to methods that have the class attribute. If you use the class attribute (for any methods in the current class definition), you are required to supply a classprefix value within the class statement. 

This attribute has no default. 

major version = number [optional] is an attribute that specifies the major version number of this class definition. Number must be in the range of 0 to (2**31)-1. This will produce bindings that will verify that any code that purports to implement this class has the same major version number, unless number is 0, in which case no test is made. 

This attribute defaults to major version = 0. 

minor version = number [optional] is an attribute that specifies the minor version number of this class definition. Number must be in the range of 0 to (2**31)-1. This will produce bindings that will verify that any code that purports to implement this class has the same or higher minor version number, unless number is 0, in which case no test is made. 

This attribute defaults to minor version = 0. 

global | local [optional] is an attribute that indicates how binding files are to be linked together. Local means link to other files in the local context first. Global means bypass the local context. For example, local will result in C-language statements like: 

    #include "file.h" 

Global will result in statements like: 

    #include <file.h> 

This attribute defaults to global. 

classinit = function [optional] allows you to provide user-written code that participates in the construction of your class. function designates a function you supply that is called when your class is created. This function receives one argument-a pointer to your newly created class object. You can use this function to perform any supplemental processing that you need. If you specify this attribute in your class definition, a template for this function will be provided automatically in the generated .C file. 

By default, your class will not have a user-written classinit function. 

description [optional] is a description of the class as a whole and must be in the form of a comment. Several comment styles are supported including: 

```
   /*
    * line1
    * line2
    */

   -- line 1 (starts with 2 consecutive dashes)
   -- line 2

   // line 1
   // line 2
```

Because OIDL files are used to generate language bindings, comments must be strictly associated with particular syntactic elements, so they will appear at the appropriate points in the output files. Therefore, comments must be placed in OIDL files with more care than in some programming languages. If you do not place your comments with strict adherence to the OIDL section syntax, the comments probably will not appear where you expect to see them. 

A fourth style for OIDL comments is referred to as throw-away comments. They may be placed anywhere in an OIDL file, because they are not intended to appear in any binding files.  Throw-away comments start with the character (#) and end at the end of the line. You can use throw-away comments to "comment-out" sections of an OIDL file. 

```
   #
   # This is an example of a throw-away comment
   #
```

Note:  Comments will appear in files produced by the SOM Compiler in various forms appropriate to the intended use of the file. Sometimes these files are intended as input to a programming-language compiler. Therefore, it is best to avoid using characters in the body of comments that are not generally allowed in most programming-language comments. For example, the C language does not allow "*/" to occur in a comment, so its use is to be avoided. 

Refer to SOM Compiler Command Syntax for information about the effect of global attributes on OIDL comments.


### Release Order Section

This optional section contains a release order statement that forces the compiler to build certain critical data structures with their items arranged in the order specified. This allows the class interface and implementation to be evolved without requiring programs that use this class be recompiled. 

Release order applies to all method names and public or private (that is, non-internal) data items. If the release order of some method or non-internal data item is not specified, it will default to an implementation-specific order based on its occurrence in the OIDL file. The introduction of new public or private data items or methods might cause the default ordering of other public or private data items or methods to change; programs using the class would then need to be recompiled. The SOM Compiler has a "pretty print" mode in which it will reproduce a class definition in a nicely formatted manner with release order specified for all relevant items. Programmers are advised to use this facility to update the release order statement whenever they make significant additions to a class. 

The syntax for a release order statement is: 

release order: name [, name ]* ; 

Example: 

```
release order: m1, m2, pd1, m3;
```

where: 

name [, name ]* [optional] contains all method names introduced by this class (whether public or private), and the names of any non-internal instance variables. It must not contain the names of any inherited methods (even if they are to be overridden), except as noted below. As the class evolves, new names can be added to the end of this list, but once a name is on this list, it must not be reordered or removed. Doing either will require the recompilation of programs that use this class. If a method named on the list is to be moved up in the class hierarchy (for example, to the parent class of this class), its name should remain just as it is on the current list, but it also must be added to the release-order list for the class that will now introduce it.


### Metaclass Section

This optional section specifies the class' metaclass, giving its name and, optionally, a description of the reason for the metaclass, or other comments about its role in this class' interface. If a metaclass is specified, its definition must be included in the include section. If no metaclass is specified, the metaclass of this class' parent class will be used. Therefore, if you intend the metaclass of this class' parent class to be used, it is generally best not to specify the metaclass. 

A class' metaclass can also be implicitly defined through the use of the class attribute in the data section or the class attribute in the method section. If you use either of these attributes you must bypass (that is, omit) the metaclass section altogether. In this case, your implied metaclass will be a subclass of the metaclass of your parent class. 

The syntax for a metaclass description statement is: 

metaclass: name; 
[description] 

Example: 

```
metaclass: FooMeta;
/*
 * This is the metaclass for the Foo class.
 * Note that several forms of comment are allowed.
 */
```

where: 

name [optional] is the name of the metaclass to be used to create the class object for this class. 

This attribute defaults to the parent's metaclass. 

description [optional] is a description of the metaclass and must be in the form of a comment (see Class Section for the discussion about comment styles). 

Note:  You can add the attributes major version, minor version, file stem, and global | local to the metaclass statement. If you include at least file stem, you do not have to include the metaclass definition in the include section.


### Parent Class Section

This required section specifies the class' parent class, giving its name and, optionally, a description of the role of the parent class in this class' interface. 

The syntax for a parent class description statement is: 

parent [class]: name; 
description 

Example: 

```
parent: SOMObject;

// Foo will be directly descended from the SOM root class, SOMObject.
// Note, this is yet another style of comment.
```

where: 

name [required] is the name of the class of which this class is a subclass. 

description [optional] is a description of the parent class and must be in the form of a comment (see Class Section for the discussion about comment styles). 

Note:  You may add the attributes major version, minor version, file stem, and global | local to the parent class statement.


### Passthru Section

This optional section provides blocks of code to be passed by the compiler into various binding files. The contents of the passed lines are essentially ignored by the compiler and can contain anything that needs to be placed near the beginning of a binding file. 

Note:  Even comments contained in passthru lines are processed without modification. 

The syntax for the passthru section is: 

[passthru: language.suffix, [ before | after ]; 
line 1 
line 2 
... 
endpassthru; [description]]* 

Example: 

```
passthru: C.h:
typedef int *foobar;
#define SIZE 89
endpassthru;
-- The two lines above will be placed in the public binding file for all C
-- language users of this class. Note: the next passthru clause has no
-- comment.
passthru: C.ih;
static char *name;
endpassthru;
```

where: 

language [required] is the programming language whose binding files are to be affected. Currently only the C language is supported. In the future other languages might be supported. 

suffix [required] specifies which binding file is to be affected. For C, the currently supported binding files are: 

.H The binding file for all users of the class 

.PH The binding file for users with access to private methods of the class 

.IH The binding file for implementers of the class 

.C The program template file used in implementing the class 

.SC The language-neutral core version of the OIDL file 

.PSC Additional language-neutral information about the private methods in the class 

.CS2 A "pretty printed" version of the OIDL file 

Note:  In general, you would not normally place passthru lines into a .C file, because a .C file is usually generated only once and then filled in with source code by a programmer. Subsequent updates to a .C file by the SOM Compiler consist only of the addition of new method templates at the end of the file. Place passthru lines needed by the class' implementation code in the .IH file instead. Because the .IH file can be completely regenerated each time the OIDL class definition is compiled, changes to your passthru lines will be automatically included. 

before | after [optional] is the attribute that indicates whether passthru lines should precede or follow any include statements at the beginning of the binding file. This attribute defaults to before. 

line [optional] is a line to be placed near the beginning of the binding file exactly as written. 

description [optional] is a description of the purpose of the passthru lines.


### Data Section

This optional section lists the instance variables for this class. This section is generally present only in the language-specific version of the class interface definition (a .CSC file). However, it must be present in the public form of the class interface definition if the class contains public instance variables. ANSI C syntax is used to describe these variables. 

The syntax for the data section is: 

data: 
[description1] 
[declaration [, private | , public | , internal] [, class]; 
[description2]]* 

Example: 

```
data:
-- This is the instance data for the Foo class.
int FooSize, public;
-- FooSize is a public instance variable.  This means that all users of the
-- Foo class will have access to FooSize.
char *fooName;
-- fooName is a private instance variable; therefore, only the implementer of
-- the Foo class will have access to it.
```

where: 

description1 [optional] is a description of the instance data as a whole and must be in the form of a comment (see Class Section for the discussion about comment styles). 

declaration [optional] is an ANSI C declaration for an instance variable. 

private | public | internal is the attribute that controls the type of binding (if any) to be exported for the instance data item. Internal prevents any binding from being exported. Private causes the binding to be part of private-usage binding files, and public causes the binding to be placed in public-usage binding files. For C, the exported binding is a macro of the form get_name(obj), where name is the name of the instance data item, and obj is an object containing the item. The macro returns an expression representing the item, which may be used on the left- or right-hand side of assignment statements. 

This attribute defaults to internal. 

class is an attribute that designates that the data item belongs to an implicitly defined metaclass. Data items having this attribute do not appear in instances of the class, but instead appear in the class itself. Methods defined in the methods section to have the class attribute can be created to manipulate class items. If you use this attribute your class definition cannot also contain an explicit metaclass section. 

By default, data items are not considered as class data. 

description2 is an optional description of the instance variable and must be in the form of a comment (see Class Section for the discussion about comment styles).


### Methods Section

This optional section lists the methods to be supported by this class. ANSI C function-prototype syntax is used to define the calling sequence to each method. 

The syntax for the methods section is: 

methods: 
[description1] 
[[group: name; 
    [description2]] 
[method prototype 
    [, public | , private] 
    [, method | , procedure] 
    [, class] 
    [, offset | , name lookup] 
    [, local | , external] 
    [, use = name]; 
    [description3]]* 
[override: method name 
    [, public | , private] 
    [, class] 
    [, local | , external] 
    [, use = name]; 
    [description4]]* 

Example: 

```
methods:
-- This section lists all the methods that are to be
-- introduced by the Foo class, as well as all the
-- methods that Foo inherits and wants to override.
void m1 (int parm1, char parm2);
-- m1 is a public method with a fixed calling sequence.
-- It does not return a value.
int m2 (), private;
-- m2 is a private method with no arguments (except
-- for its target object) that returns an int.
long m3 (int parm1), procedure;
-- m3 will be a simple procedure.  It cannot be overridden.
-- It will still have a "somSelf" argument like any other method.
group: g2;
-- The rest of the methods listed in this section are
-- in group "g2".
int m4 (int numargs, ...);
-- m4 is a public method that has one required argument
-- and any number of additional arguments that can be
-- of any types.
override: somInit;
-- This class will override the implementation of
-- somInit that it inherits from one of its ancestor
-- classes.
override: m6, private;
int m5 (int p1, /* first parameter */
        int p2, /* second parameter */
        char *p3 /* last parameter */);
-- Note how comments can be embedded in the method
-- prototype.
```

where: 

description1 [optional] is a description of this class' methods as a whole and must be in the form of a comment (see Class Section for the discussion about comment styles). 

name [required in each group statement] is the name of this group. Currently, groups serve no purpose except to improve the readability of the object interface definition. 

description2 [optional] is a description of this group of methods as a whole and must be in the form of a comment (see Class Section for the discussion about comment styles). 

<method prototype> [required in each method specification] is the ANSI C function prototype that defines the calling sequence to this new method with the two exceptions below: 

 1.Even though the first parameter to each method is the target object, this object is not mentioned in the method prototype. 

 2.Each parameter can be preceded by one of, IN, INOUT, or OUT, indicating whether it is an input, input/output, or output parameter. 

Comments can occur after the separating comma between parameter specifications and after the last parameter, but before the closing parenthesis (see the declaration of m5 in the example above). 

public | private [optional] is an attribute that indicates to the compiler whether or not this method is part of the public interface to this class. There is no real difference between public and private methods, but the compiler will separate the bindings to these two classes of methods so that bindings for public methods can be distributed without distributing bindings for private methods. 

This attribute defaults to public. 

local | external [optional] is an attribute that directs the compiler to declare the method function for this method as an external name or as a local name (directly accessible only to the compilation unit in which it occurs). 

When specified, this attribute overrides the class default for method functions (see the descriptions for function prefix and external prefix under Class Section). 

This attribute defaults to the class default. 

This attribute has not been implemented at this time. 

use = name [optional] is an attribute that tells the compiler that the method function for this method is to have the name name. This overrides any class prefix specification. 

This attribute has no default. 

This attribute has not been implemented at this time. 

method | procedure [optional] is an attribute that indicates whether or not this method can be overridden by a subclass. 

If method is specified, the method will operate on instances of the class and can be overridden by a method in a subclass. 

If procedure is specified, the method will be a simple procedure. None of the normal method resolution mechanisms will be used in invoking the method procedure; it will be called directly. 

This attribute defaults to method. 

class is an attribute that specifies whether the method operates on instances or the class itself. 

If class is specified the method is considered to be associated with an implicit metaclass. In this case the method will operate directly on the class itself and not on its instances. This is a convenient way of defining constructors or factory methods that can be invoked when no object instances exist. The implicit metaclass is considered to be a subclass of the parent class' metaclass. If you use the class attribute you cannot also define an explicit metaclass section. In addition, you must also supply a classprefix value in the class statement (see Class Section). 

If this attribute is omitted, the method is assumed to operate on object instances rather than the class. 

offset | name lookup [optional] is an attribute that indicates the preferred invocation binding to be used for this method. Generally, methods are invoked on the basis of information provided by the class that introduces the method definition (called offset resolution). However, this requires that the class of the method's target object be known at compile time. Sometimes a method definition is introduced by several classes. For such methods, name lookup (which invokes the method using the method's name as a key) is a more appropriate choice. 

This attribute defaults to offset. 

description3 [optional] is a description of the method and must be in the form of a comment (see Class Section for the discussion about comment styles). 

method name [optional] is the name of a method introduced by an ancestor class that this class will re-implement. Attributes on an override method have the same meaning as previously stated for new methods. 

description4 [optional] is a description of the override method or of your reason for overriding it, or both, and must be in the form of a comment (see Class Section for the discussion about comment styles).


### Sample VECTOR.CSC file in OIDL

```
#include <somobj.sc>   # Include the parent class definition

class: Vector,
        file stem = vector,
        external prefix = vect,
        classprefix = mvec,
        major version = 1,
        minor version = 0;

-- Demo class definition that implements a simple vector-of-integers
-- object. Vector elements are numbered from 0.  The size of the
-- vector must be set before using the array (otherwise it raises an
-- error) and cannot be changed once it is set.
-- This is a comment.

parent: SOMObject;

passthru: C.h;
/* something to put in the VECTOR.H file */
endpassthru;

passthru: C.ph;
/* something to put in the VECTOR.PH file */
endpassthru;

passthru: C.ih;
/* something to put in the VECTOR.IH file */
endpassthru;

data:

    integer4 (*body)[], public;

    -- <body> is a public instance variable, and therefore accessible in
    -- any code that has access to this class.  It is accessed via a macro
    -- of the form get_body(obj) where obj is the object whose instance of
    -- body you are accessing.  The macro expression can be used on the
    -- right- or left-hand side of an assignment.

    int size;

    -- <size> is an internal instance variable, and therefore accessible
    -- only in the code that participates in the implementation of this
    -- class.

methods:

SOMAny *newVectorOfSize(int size), class;

-- Creates a new instance of Vector and sets its size to <size>.

integer4 get (int i);

-- Returns the <i>th element in the vector.  Raises an error if
-- this vector does not have an <i>th element.

void set (int i, integer4 value);

-- Set the <i>th element of this vector.  Raises an error if
-- this vector does not have an <i>th element.

void setMany (int start, int num, ...);

-- Set several elements at once.  You must provide <num> elements, and
-- they will be assigned to vector elements starting with <start>.
-- Raises an error if this vector does not include each of the positions
-- covered by the assignment.

void setAll (integer4 value),
        private;

-- Sets all the elements in this vector to <value>.
-- Note: This is a private method and is not available for use unless
-- one has access to the private header file.  It would not appear in
-- the VECTOR.SC file.

void setSize (int size)

-- Set the size of a vector;
-- Use this method to establish the capacity of any Vector instance
-- created by the VectorNew macro (as opposed to instances created
-- with the newVectorOfSize constructor), before putting anything in
-- the vector.

override somInit;
-- Method prototype:
-- void somInit(Vector *somSelf);

-- Add initialization of the vector instance data.

override somDumpSelfInt;
-- Method prototype:
-- void somDumpSelfInt(Vector *somSelf, int level);

-- Add output of the vector instance data.
```


## SOM Compiler

The SOM Compiler translates the OIDL source definition of a SOM class into a set of bindings appropriate for a particular programming language. The SOM Compiler supplied with the OS/2* 2.0 Toolkit produces a complete set of bindings for the C programming language. 

The compiler operates in two phases-a precompile phase and an emission phase. In the first phase a precompiler (SPC.EXE) reads and analyzes a user-supplied class definition and produces intermediate output files containing binary class information, comments, and passthru lines). In the second phase, one or more "emitter" programs (EMITC.EXE, EMITH.EXE, EMITIH.EXE, EMITPH.EXE, EMITDEF.EXE, EMITSC.EXE, EMITPSC.EXE, and EMITCSC.EXE) run to produce C-language binding files. Two additional programs (SPP.EXE and SPP2.EXE) serve as preprocessors for the SOM precompiler phase. The sequencing and execution of all of these programs is directed by the SOM Compiler (SC.EXE). 

The output from the emitters, plus user-supplied logic for the class' methods, are subsequently compiled by the C compiler and linked by the OS/2* 2.0 linker to create an executable program. Executable code can be packaged in self-contained .EXE files or placed in a DLL so the class can be used from many programs. 

The emitters for C produce the following output files: 

Output File Contents 

<class-stem>.C A template for a C source program that implements a class. If you are implementing a SOM class in C, this will become your primary source file. It contains stub procedures for all of the methods defined in the <class-stem>.CSC file. Once you have supplied your own logic for these methods, subsequent processing by the .C emitter will make only "incremental" updates to your source file, based on changes that you make to the class definition. These incremental updates consist of additional method templates that are appended to the end of your .C file if you have subsequently defined new methods in your class definition. 

The generated .C source file contains an include statement for the .IH file described below. 

If you are writing only "client" code that accesses a SOM class someone else has implemented, you do not need to generate a .C file. 

<class-stem>.H This is the public include file for all C-language programs that need to access the SOM class. It contains a tailored set of C macros for accessing the public methods and the public instance data of the class. It also contains a macro for creating new instances of the class, and includes several other header files (based on the class definition), such as the .H files for the parent class and the metaclass, as well as the principal header file for SOM (SOM.H). 

<class-stem>.IH This file is referred to as the implementation header. It is included from the <class-stem>.C file and contains most of the automatically generated implementation details about your class. The information found here includes: 

oA C struct defining your class' instance data. 

oC macros for accessing your internal instance data. 

oC macros for invoking parent methods that your class has overridden. 

oA <className>GetData macro used by the method stubs in your .C file to set the "somThis" pointer. 

oAn apply stub for each of the new methods in the class. 

oA <className>NewClass procedure for constructing your class object at run time. 

<class-stem>.PH This file contains use macros for any private methods defined in the class (the .IH file will have a #include for this file if your class has private methods), as well as macros for any instance data items designated as private. This file should be distributed only to users who need knowledge of (and access to) your private methods. 

<class-stem>.DEF This file can be used by the OS/2* 2.0 linker to package your class in a DLL. If you want to combine several classes into a single DLL, merge the exports statements from each of their .DEF files into a single .DEF file for the entire DLL. When placing multiple classes in one DLL you also must write a simple C procedure named "SOMInitModule" and include it in the export list. This procedure will be called by the SOM Class Manager whenever your DLL is dynamically loaded, and it should call the <className>NewClass routine of each class in your DLL. Like all SOM functions and methods, your "SOMInitModule" routine should adhere to OS/2* 2.0 system linkage conventions. 

<class-stem>.SC The language-neutral form of the SOM class definition. It is a proper subset of the .CSC file with all private implementation detail removed. If you wish to publish your class for others to use, this is the form of the OIDL class definition that you should publish. A .SC file also can be used as input by the SOM Compiler, which can use it to generate a .H file for use by programs that are clients of the class. 

<class-stem>.PSC A supplement to the language-neutral .SC file that contains information about the private methods of a class. The .PSC file contains everything needed for subsequently generating a .PH file. 

<class-stem>.CS2 A "pretty-printed" form of your original .CSC file, with all of the elements arranged in a canonical form. If you want the SOM Compiler to produce a release order section for you automatically, you can obtain it from this file. The .CS2 file will have the same content as the original .CSC file except that its release order statement will always be complete (even if the release order statement in the .CSC file is not), and a consistent comment style will appear throughout. 

Of the files discussed here, two of them (the .CSC file and the .C file) should be treated as primary source materials and kept in your development library. The remaining files can be generated from your .CSC file whenever your class is built, or whenever its definition changes.


### Running the SOM Compiler

The SOM Compiler is actually a precompiler and a collection of code emitters that take the intermediate output from the precompiler and produce files for a variety of purposes and in several forms including, C header files, a C implementation template, and language-neutral core interface files. 

Assume that you have defined the interface for a class called Example and that you placed the definition in a file called EXAMPLE.CSC (.CSC is the standard extension for the C-specific form of an OIDL file). Then you might execute the following statement: 

```
    SC EXAMPLE
```

to compile EXAMPLE.CSC and produce the desired C-language binding files. SC.EXE uses three user-defined environment variables to control its operation and determine which emitters to execute: SMINCLUDE, SMEMIT, and SMTMP.


#### The SMINCLUDE Environment Variable

The SOM Compiler uses an environment variable named SMINCLUDE to locate included class definitions. Because every SOM class will have an include for its parent class definition, you will need to set this variable before running the SOM Compiler. It is similar in form to the OS/2* PATH or DPATH environment variables, in that it can consist of one or more directory names separated by a semicolon (;). Directory names can be specified with absolute or relative path names. For example 

```
    SET SMINCLUDE=.;..\MYSCDIR;C:\TOOLKT20\C\INCLUDE;
```


#### The SMEMIT Environment Variable

SMEMIT is used to indicate which emitter programs should be executed. Like the SMINCLUDE environment variable it can consist of a list of items separated by semicolons. Each item designates a particular emitter by the name of the file extension the emitter produces. For example 

```
    SET SMEMIT=H;IH;PH;SC;DEF;
```

indicates that the EMITH.EXE, EMITIH.EXE, EMITPH.EXE, EMITSC.EXE and EMITDEF.EXE programs should be executed to produce .H, .IH, .PH, .SC, and .DEF files, respectively. By default all emitted output files are placed in the same directory as the input file named in the SC command. If the SMEMIT environment variable is not defined, the SOM Compiler will perform a syntax check of your class definition but no output will be produced.


#### The SMTMP Environment Variable

The SMTMP environment variable specifies the name of a directory that the SOM Compiler uses to hold intermediate output files. For example, 

```
    SET SMTMP=%TMP%
```

tells SC.EXE to use the same directory for temporary files as given by the setting of the TMP environment variable. 

As a general rule, the directory indicated by SMTMP should never coincide with the directory used by the SOM Compiler for its input or the emitted output files. If you do not give a setting for the SMTMP environment variable, SC will use the root directory of the current drive for temporary files.


### SOM Compiler Command Syntax

The syntax of the command for running the SOM Compiler (SC.EXE) is: 

    SC [-options] file[.CSC] 

where options can be specified individually, as a string of option characters, or a combination of both. Any option that takes an argument either must be specified individually or appear as the final option in a string of option characters. 

The file specified with the SC command refers to the file containing the OIDL class definition to be compiled. Typically this file will have a .CSC or .SC extension, but this is not required. If a file exists with the given name, that file will be used. If no such file exists, a .CSC extension is assumed. 

The available options are 

-C n set the size of the comment buffer (default: 32767). 

-S n set the total amount of string space for names and passthru lines (default: 32767). 

-V display version information. 

-a name[=value] add a global attribute. The currently supported attributes are defined below (at the end of this section). 

-d directory specify a directory where all files emitted during the execution of this command should be placed. If the -d option is not used, all emitted output files are placed in the same directory as the input .CSC file. 

-h or -? provide usage information for reference. 

-i filename specify the name of the OIDL class definition file. Use this option to override the built-in assumption that the input file will have a .CSC extension. Any filename you supply with the -i option is used exactly as you provide it. 

-r check that all release-order entries actually exist (default: FALSE). 

-s string substitute string in place of the contents of the SMEMIT environment variable for the duration of the current SC command. If you supply a list of values, you must enclose the list with double quotation marks (""). You can use the -s option as a convenient way to override the SMEMIT environment variable. For example: 

    SC -s "h;sc" EXAMPLE 

is equivalent to the following sequence of commands: 

    SET OLDSMEMIT=%SMEMIT% 
    SET SMEMIT=h;sc 
    SC EXAMPLE 
    SET SMEMIT=%OLDSMEMIT% 

-w suppress warning messages (default: FALSE). 

The only global attributes currently supported by SC.EXE are: 

comment=comment string where comment string can be one of the following: "/*", "--", or "//". This indicates that comments marked in the indicated way are to be completely ignored by SC.EXE and not retained for subsequent processing by one of the emitters. 

Note:  Comments indicated by lines whose first non-white-space character is a # are always ignored by SC.EXE. Also note that comments of any form in passthru lines are passed through. 

cstyle=comment style controls the form of emitted comments. Comment style must be one of s, c, or + to cause emitted comments to be in "--", "/* */", or "//" form, respectively. The default form is s. 

ibmc causes EMITC, EMITH, EMITIH, EMITPH, and EMITDEF to generate code with pragmas specifically intended for the IBM C Set/2 Compiler. This attribute is specified by default. 

cl386 causes EMITC, EMITH, EMITIH, EMITPH, and EMITDEF not to generate code with pragmas specifically intended for the IBM C Set/2 Compiler.


## SOM bindings for C

The form of the SOM Application Programming Interface (API) varies depending on the programming language that you are using.  The API described here corresponds to the form that a C-language programmer would use. 

Three of the output files produced by the SOM Compiler can be considered as C-language binding files. 

<class stem>.H The public-usage binding file. This file must be included in a C-language program in order to use objects of the class. 

<class stem>.PH The private-usage binding file. This file must be included in a C-language program in order to use the private parts of the class' interface. 

Note:  This file includes the <class stem>.H file. 

<class stem>.IH The implementation binding file. This file must be included in the source file that implements the class. 

Note:  This file includes the <class stem>.PH file, if one exists, otherwise it includes the <class stem>.H file. 

In addition, compilation of a .CSC file for a class can produce or update the <class stem>.C file that contains the class' implementation. 

All C-language binding files produced by the SOM Compiler are protected with an appropriate #ifndef so that they can be included in a C-language compilation unit more than once without harm.


### API for Class Clients

Programs that use or subclass a class are referred to as client programs.  To be a client of a class, your C-language program must include the <classstem>.H file generated by the SOM Compiler. This header contains a customized set of macros for using all of the class' public methods and accessing all of its public instance variables from a C-language program. 

A special header (SOM.H) contains, or includes, all of the usage macros for the classes and methods supplied as part of SOM itself. This header is automatically included by any generated <classstem>.H file, or can be included explicitly.


#### <className>NewClass

The C-language interface to a class also includes a function whose name is <className>NewClass. This is a standard C function (not a method) produced by the SOM Compiler for creating the actual SOM class object.  Its interface is given by: 

```
    SOMAny *<className>NewClass (int majorVersion, int minorVersion);
```

This function will create the class object (if it does not already exist), and return a pointer to it.  If the SOM run time has not yet been initialized, this function will initialize it prior to constructing the class.  The user-supplied version numbers are checked against the version information built into the class to determine if the class is compatible with the user's expectations.  If the class is not compatible, an error condition is raised and (*SOMError)() is invoked. See the discussion under "somCheckVersion" in the Methods Reference section for more information about version number-checking. 

Note:  Constructing a class might also cause the dynamic loading or construction of its parent class or classes and its metaclass. After the first call to this routine, subsequent invocations bypass the class construction and simply return a pointer to the existing class object.


#### <className>New

This macro can be used to create an instance of class <className>.  It takes no arguments and returns a pointer to a new object instance.  If the class object does not already exist, this macro first creates the class object.  Its interface is given by: 

```
    SOMAny *<className>New();
```

If a new instance cannot be created an error condition is raised and (*SOMError)() is invoked.  This macro is a convenient shorthand for applying the built-in somNew method to the appropriate class object, as in 

```
    SOMAny *aNewInstance;
    aNewInstance = _somNew(<className>NewClass());
```


#### <className>Renew

The <className>Renew macro can be used to create an instance of class <className> in a block of memory supplied by the calling program.  Its operation is identical to the <className>New macro, except that no memory is allocated for the new object instance. 

```
    SOMAny *<className>Renew(SOMAny *buf);
```

The argument buf must point to a block of storage large enough to hold an instance of class <className> (you can used the built-in SOM method, somGetInstanceSize, to determine the amount of memory required).


#### _<className>

This macro serves as a convenient way to refer to the class object created by the <className>NewClass macro. You need to be certain that the class has been created prior to any use of this macro.


#### Method Macros

The C-language macro form of a SOM method invocation consists of an underscore character (_) immediately followed by the method name. This token, when combined with an argument list using standard C function syntax, indicates a method call. 

All SOM methods require at least one argument-a pointer to the receiving object, followed by additional arguments, if any, appropriate to the particular method to be invoked. 

Note:  This first argument (the receiving object) is not listed when the method definition is specified in the class definition, because this is more an artifact of the method resolution mechanism than a logical argument to the method. However, when the method is actually invoked, the receiving object must be passed to the method as the first parameter. This argument designates the object to which the method applies. 

If you use a C expression to represent or compute this argument, you must confine your usage to expressions without side-effects, as this first argument is actually evaluated twice by the macro expansion. In particular, the following usage is always incorrect: 

```
    HPS targetPresentationSpace;
    SOMClass *VisualObject;
    ...
    _displayYourself (_somNew(VisualObject), targetPresentationSpace);
    /* _somNew() is incorrect in this context */
```

Instead, code: 

```
    SOMAny *temp;
    ...
    temp = _somNew (VisualObject);
    _displayYourself (temp, targetPresentationSpace);
```

The correct code above replaces an expression with side-effects (_somNew()), with one that can be harmlessly evaluated multiple times (temp). 

For a typical example of method invocation in C, consider these methods from the sample VECTOR.CSC file: 

```
    methods:

        SOMAny *newVectorWithSize(int size), class;
        void set (int i, integer4 value);
        integer4 get (int i);
        void setMany (int start, int num, ...);
```

The first three of these could be invoked using the following code sequence: 

```
    SOMAny aVector;
    int i;

    VectorNewClass(1,0); /* Ensure that the class exists */
    aVector = _newVectorOfSize(_Vector,5);

    /* Set aVector to the 1st 5 even numbers */
    for (i=0; i<5; i++)
        _set(aVector, i, i*2);

    printf("The value of the 3rd element is %ld\n",
           _get(aVector,2)); /* Elements are 0-origin */
```

The _newVectorOfSize method is a constructor for Vector objects (indicated by the class attribute in its definition in VECTOR.CSC). Because this method operates on the Vector class rather than on an instance the receiving object is indicated as _Vector. The other methods in this example then operate on the newly created instance, aVector. 

Methods that are defined to take a varying number of arguments can also be invoked using macros like those shown above. In addition, the SOM Compiler generates a special function for each method requiring a variable argument list. These functions have "va_" as a prefix to the method name. The setMany method shown above could be invoked in either of the following ways 

```
    _setSize(aVector,7);
    _setMany(aVector, 2, 5, 4L, 6L, 8L, 10L, 12L);

    or

    _setSize(aVector,7);
    va_setMany(aVector, 2, 5, 4L, 6L, 8L, 10L, 12L);
```

Note:  SOM uses the convention that all method names begin with a lowercase letter; uppercase characters are used to emphasize word boundaries within the method name.  However, you are free to use any convention you like for methods that you define. Another SOM convention is that all public static methods that have the same name, also should have a common signature. That is, they should return values of the same type, and take arguments that agree in number and type. Consequently, it is good practice to use a unique prefix or suffix whenever practical to avoid accidental duplication of method names.


#### SOM_Resolve and SOM_ResolveNoCheck

In addition to the individual C-language macros for invoking methods, SOM supplies two macros (SOM_Resolve and SOM_ResolveNoCheck) that can be used to invoke any static method (static methods are those accessible through offset resolution). The difference between these two macros is that SOM_Resolve performs consistency checking on its arguments while SOM_ResolveNoCheck, which is faster, does not. Both macros require the same three arguments as shown below: 

```
    SOM_Resolve(<receiver>,<className>,<methodName>)
    SOM_ResolveNoCheck(<receiver>,<className>,<methodName>)
```

<receiver> is the object to which the method will apply. As with the method macros, <receiver> should be given as an expression without side-effects. <className> is the name of the class of the receiving object, and <methodName> is the name of the desired method. These names are supplied as simple tokens rather than strings. The macro evaluates to an expression that represents the actual entry-point address of the method procedure.  This value can be stored in a variable and retained so that subsequent method resolutions directed to the same receiving object can be bypassed altogether. Cast this result to be of the same type as the method procedure to which it refers.


#### Public or Private Instance Variable Macros

Instance variables that have been declared to be public or private can be accessed directly by clients of a class, using a macro of the form: 

```
    get_<instanceVariableName>(<targetObject>)
```

Here, <instanceVariableName> is the name of the public or private instance variable to access, and <targetObject> is a pointer to the object where the instance variable resides.  This macro can be used on either side of the equal sign (=) in a C assignment statement. 

(The macros for accessing private instance data items are only found in the .PH file, whereas the public instance data macros appear in the class' .H file.)


### API for Class Implementers

Programmers who implement SOM classes in C can use all of the client programmer APIs, as well as several additional macros that are not available in client programs. 

The C-language implementation of a SOM class is contained in one or more .C files. If more than one .C file is needed, one (and only one) of them is considered the "primary" file and includes the following #define statement: 

```
    #define <className>_Class_Source
```

This is used in the SOM-generated .IH file to determine when to define various functions associated with the class, such as the <className>NewClass function.  As a matter of course, all .C files must include the .IH file.  The skeletal .C files generated by the SOM Compiler contain a #include statement for the .IH file; any additional .C files you create for the class should be modelled after these.


#### Implementation Conventions for Methods

The macros that the SOM Compiler produces for use by method implementers presume certain conventions. Because each SOM method always receives at least one argument-a pointer to the object that the method should apply to, this argument is given the name "somSelf." 

"somSelf" is defined to be a pointer to an object that is an instance of class <className> or an instance of one of its descendent classes. Consequently, the object pointed to by "somSelf" can contain sections with instance data from any number of classes related through inheritance. A local variable named "somThis" is used by each method implementation to access the instance data in its class' section of the object. 

The "somSelf" pointer is always passed to the method procedure as an argument; the "somThis" pointer must be set by each method that needs access to instance data. A custom macro, <className>GetData, is provided for each class in its .IH file to derive the appropriate value for the "somThis" pointer from the "somSelf" pointer. This housekeeping is performed automatically in the method stubs generated by the SOM Compiler, but you need to be aware of this convention. You can use the "somThis" pointer either explicitly to manipulate your instance data, or implicitly by using custom macros for each item of instance data.


#### <className>GetData Macro

If you are implementing a class that contains instance variables most of the methods in your class will need addressability to the instance data.  The SOM Compiler generates a C typedef with the name <className>Data for the structure that it uses to hold your instance data.  Methods that will access the data then use the <className>GetData macro to establish addressability.  This macro must be one of the first executable lines of code in each method, and the value it returns should be assigned to a local variable named "somThis." The SOM Compiler automatically generates the code that accomplishes this in each method stub in a .C file. 

Here is a sample method implementation from the .C file derived from the sample VECTOR.CSC class definition. 

```
    #pragma linkage (system, get)                    /* Generated line */
    static long SOMLINK get(Vector *somSelf, int i)  /* Generated line */
    {                                                /* Generated line */
        VectorData *somThis = VectorGetData(somSelf);/* Generated line */
        VectorMethodDebug("Vector","get");           /* Generated line */

        if (i<_size)                      /* These lines were supplied */
            return (*_body)[i];           /* by the implementer of the */
        else                              /* method.                   */
            SOM_Error (10+SOM_Fatal);     /*                           */

        return ((long) 0);                           /* Generated line */
    }                                                /* Generated line */
```

The above example shows a typical usage of the <className>GetData macro.  It takes a single argument, <somSelf>, defined to be a pointer to the object "receiving" the method call, and returns a pointer to the portion of the object that contains the instance data structure for class <className>.


#### Instance Variable Macros

If your instance data consists of items with the names <a, b, c> the .IH file produced by the SOM Compiler will have custom macros formed by prefixing an underscore character (_) to each item, resulting in macro names of <_a, _b, _c>. These macros assume that a local variable named "somThis" has been set to point to the portion of the object instance where your instance data is kept. You can use these macro names for your data items anywhere one of the original names would have been valid.


#### Parent Method Macros

If you define methods in your class that override those inherited from one of your parent classes, you will frequently want to write your own logic as incremental changes to the parent methods' behavior. That is, at some point within your method, you will need to invoke the parent method to perform its own processing.  This could occur at the beginning of your method code, at the very end, or at some point in the middle, depending on the nature of the inherited method and how you intend to supplement or modify its behavior. 

To be certain that the method-resolution mechanism will bypass your (overriding) method and invoke the parent method instead, macros are provided in the <className>.IH file (for each overridden method) that start with the prefix "parent_". For example, if you have methods <m1> and <m2> that override parent methods, the macros <parent_m1> and <parent_m2> can be used in your code to invoke the parent methods when needed.


#### SOM_ParentResolve

Just as SOM_Resolve is available to clients of a class, the SOM_ParentResolve macro can be used by class implementers, within the body of a method procedure, to obtain the entry-point address of a parent-method procedure. This value can be saved and subsequently used to bypass the method-resolution process when invoking a parent method. Like SOM_Resolve it applies only to static methods. It requires three arguments as shown below: 

```
    SOM_ParentResolve(<parentClassName>,<className>,<methodName>)
```

<parentClassName> is the name of the parent class, <className> is the name of the class where the macro appears, and <methodName> is the name of the desired parent method. These names are supplied as simple tokens rather than strings. The macro evaluates to an expression that represents the actual entry-point address of the parent-method procedure. Cast this result to be of the same type as the method procedure to which it refers.


### API for General Usage

The interfaces described here can be used both in programs that are are clients of a SOM class and programs that implement SOM classes. To use the general-purpose SOM macros, you need to include <SOM.H>, or any .H file produced from the SOM Compiler.


#### ID Manipulation

IDs are essentially numbers that uniquely represent strings. They are used in SOM to identify method names, class names, and descriptors. All SOM ID manipulations are case-insensitive, although the original case is always preserved. A set of macros to do convenient ID manipulation is provided as part of the SOM C bindings. The syntax of the ID macros is shown below: 

```
    #include <som.h> /* or any SOM class .h file */
    SOM_CheckId(id)
    SOM_CompareIds(id1,id2)
    SOM_StringFromId(id)
    SOM_IdFromString(str)
```

An ID starts as a pointer to a string (that is, a pointer to a pointer to an array of zero-terminated characters). During its first use with any of the above macros, it is automatically converted to an internal id representation. You can perform this transformation explicitly yourself using the SOM_CheckId macro. Because the representation of an ID changes during this process, a special SOM typedef (somId) is provided to declare IDs. You can statically declare an ID, or generate one dynamically from a string. Here is an example of a statically declared ID and a dynamically created one: 

```
    /* Statically declared ID */

    zString example = "exampleMethodName";
    somId exampleId = &example;

    /* Dynamically created ID */

    somId myClassId;
    myClassId = SOM_IdFromString ("MyClassName");
```

SOM_CompareIds is a fast and efficient way to determine whether the strings the IDs represent are equal. 

There are also a set of functions included in the SOM run-time library that allow you to exert finer control over the creation and use of IDs. These are: 

```
    int           somRegisterId(somId id);
    unsigned long somUniqueKey(somId id);
    unsigned long somTotalRegIds(void);
    void          somSetExpectedIds(unsigned long numIds);
    void          somBeginPersistentIds(void);
    void          somEndPersistentIds(void);
```

somRegisterId is identical to the SOM_CheckId macro, but, in addition, returns an indication of whether the string associated with the argument ID was already known (1 indicates that the string was already known; 0 that it has been newly registered). 

somUniqueKey returns a numeric value that uniquely represents the string associated with the argument ID. 

somTotalRegIds returns the number of IDs that have been registered so far. You can use this value to advise the SOM run time about expected ID usage in later executions of your program by specifying it in a call to somSetExpectedIds 

somSetExpectedIds, if used, must be called prior to any explicit or implicit invocation of somEnvironmentNew. It allows you to specify the number of unique IDs you expect to use during the execution of your program. This has the potential of slightly improving your program's space and time utilization (if the value you specify is accurate). 

Note:  This is the one and only SOM function that can be invoked prior to somEnvironmentNew. 

The somBeginPersistentIds and somEndPersistentIds functions are used to delimit an interval of time for the current thread during which any new IDs that are used (by SOM_CheckId, SOM_IdFromString, or the somRegisterId function) are guaranteed to refer only to static strings that will not be subsequently freed. (Under normal usage the only time a static string would be freed is when a .DLL in which it resides is unloaded). IDs that are registered within a "persistent ID" interval can be handled quicker and more efficiently because there is no need to create a copy of the strings they reference.


#### Debugging Facilities

The SOM run time has several facilities for conditionally generating stream-oriented character output.  All output characters generated by these facilities ultimately pass through a replaceable procedure called SOMOutCharRoutine. The default version of this routine simply writes the character output to stdout, but you can replace this procedure with one that routes its output to a window or any other destination of your choice. 

Depending on the macros employed, debugging output can be conditionally suppressed or produced based on the setting of three global variables: SOM_TraceLevel, SOM_WarnLevel, or SOM_AssertLevel. 

Variable Macros/Functions 

SOM_TraceLevel <className>MethodDebug 

SOM_WarnLevel SOM_WarnMsg, SOM_TestC, SOM_Expect 

SOM_AssertLevel SOM_Assert 

[Unconditional] somPrintf 

<className>MethodDebug 

```
    char *class;
    char *method;

    <className>MethodDebug (class, method);
```

This custom macro is generated as part of the method stubs produced by the .C emitter.  It takes two arguments-a class name and a method name-and if SOM_TraceLevel has the value 1 or 2, produces a message each time a method is entered.  (Setting SOM_TraceLevel to 2 also causes the methods supplied as part of the SOM run time to generate method trace output.)  To suppress the generation of method tracing code, place a line similar to the following in your .C file after the #include statement for <classStem>.IH: 

```
    #define <className>MethodDebug(c,m) SOM_NoTrace(c,m)
```

SOM_TestC 

```
    SOM_TestC (condition);
```

This macro takes an arbitrary Boolean expression as an argument. If the expression evaluates as true (non-zero), execution continues; otherwise SOM_Error is invoked with a warning-level error code. If SOM_WarnLevel is set to 1 or 2, a warning message also is produced (the value 2 will include warning messages produced by the SOM run time code). 

SOM_WarnMsg 

```
    char *msg;

    SOM_WarnMsg (msg);
```

This macro writes out the string msg if SOM_WarnLevel is set to a value of 1 or 2 (a value of 2 also results in warning messages generated from the SOM run-time code). 

SOM_Assert 

```
    integer4 errorCode;

    SOM_Assert (condition, errorCode);
```

This macro allows you to place assertions in your code.  The assertion is expressed as an arbitrary Boolean expression that is required to evaluate as true (non-zero).  If the assertion fails, the SOM_Error macro is invoked using the error code you supply here. 

SOM_Expect 

```
    SOM_Expect (condition);
```

This macro is similar to SOM_Assert, except that if the condition indicated is not true, a SOM_WarnMsg macro is used to produce a warning message to that effect. 

somPrintf 

```
    int charCount;
    zString fmt;

    charCount = somPrintf (fmt, ...);
```

somPrintf is a function that unconditionally generates character stream output and passes it to (*SOMOutCharRtn)().  The interface to somPrintf is identical to that for the printf C library routine. 

Validity-Checking Method Calls 

In addition to the explicit use of debugging macros, the SOM C-language bindings produce code that automatically performs basic validity checking at run time for all SOM method invocations.  If any of these basic checks fail, the SOM_Error macro is used to end the process. Once you have tested your code to your satisfaction and are confident that it is working correctly, you can remove the automatic validity checking by placing the following #define in your .C source file prior to the #include statement for the <className>.IH file. 

```
    #define SOM_NoTest
```


#### Error-Handling Facilities

SOM error handling is performed by a user-replaceable procedure that produces a message and an error code and can, if appropriate, end the process where the error occurred. See SOMError for specifics about the interface to the error-handling procedure. 

Each error is associated with a unique integer value referred to as an error code. Errors detected by the SOM run-time environment, and their associated error codes, are listed in the Error Codes Appendix. 

Errors reported through SOM fall into 3 categories: 

SOM_Ignore This classification represents an informational event; it is considered normal, and could be ignored or logged at a user's discretion. 

SOM_Warn This category is for unusual conditions that are not considered to be normal events, but that are not severe enough in themselves to require abnormal termination of a program. 

SOM_Fatal Errors classified as fatal represent conditions that either should not occur or that would result in an intolerable loss of system integrity if processing were allowed to continue.  These errors should typically cause the termination of the process in which they occur. 

These error classifications are each assigned a single numeric value carried in the low-order digit of the error code. 

SOM_Error Macro 

```
    int errorCode;

    SOM_Error (errorCode);
```

The SOM_Error macro takes a SOM error code and invokes the error-handling function passing the error code, the name of the source file, and the line number within the source file where the macro was invoked. The default error-handling function supplied with SOM will provide this information in the form of a message routed through SOMOutCharRoutine. Additionally, if the low-order digit of the error code indicates a serious error (value SOM_Fatal), the process also is ended; otherwise, control returns to the invoking routine. 

SOM_Test 

```
    SOM_Test (condition);
```

This macro takes an arbitrary Boolean expression as an argument. If the expression evaluates as true (non-zero), execution continues; otherwise, SOM_Error is invoked with a fatal error code.


#### SOM_GetClass

```
    SOMAny *object;
    SOMClass *class;

    class = SOM_GetClass (object);
```

This macro takes a single argument that is a pointer to an arbitrary SOM object and returns a pointer to its class object.  All SOM class objects support a variety of methods that return information about the content and characteristics of the objects they can create.  See "SOMClass" in the Classes Reference section for further information.


#### SomEnvironmentNew

```
    SOMClassMgr *SomEnvironmentNew ();
```

This is a procedure that can be used to initialize the SOM run-time environment explicitly. Although no other SOM facilities can be used until this has been accomplished (see ID Manipulation for a minor exception to this rule), it is not generally necessary to call this procedure overtly, because all <className>NewClass procedures, as well as all <className>New and <className>Renew macros invoke this function implicitly if it is needed. Upon completion somEnvironmentNew returns SOMClassMgrObject. This object is the single instance of SOMClassMgr class that is present in every SOM run-time environment.


## Customization features

SOM is designed to be policy free and highly adaptable. Most of the SOM behavior can be customized by subclassing the built-in classes and overriding methods, but the SOM run time also makes use of a small number of OS/2* 2.0 facilities. You can override any use of OS/2* system facilities in the SOM run time by supplying your own replacements for the default SOM system-interface routines. You can substitute your replacement routine by placing its entry-point address in one of the following external variables. Because SOM operates within a process, your replacement routine will affect only the active process. 

Replacement routines should be written in C and adhere to standard OS/2* 2.0 system calling conventions. 

Replaceable entry points: 

SOMCalloc 
SOMClassInitFuncName 
SOMDeleteModule 
SOMError 
SOMFree 
SOMLoadModule 
SOMMalloc 
SOMOutCharRoutine 
SOMRealloc


### Memory-Management Functions

The memory management functions used by the SOM run-time environment are a subset of those supplied in the ANSI C standard library. They have the same calling interface and return the same types of results as their ANSI C equivalents, but include some supplemental error checking. Errors detected in these functions result in the invocation of the (*SOMError)() function with an appropriate error code. 

The correspondence between the SOM memory-management procedure variables and their ANSI standard library equivalents is given in Table 1 below. 

```

SOM Procedure     ANSI Standard      Return   Argument
  Variable      C Library Routine     type     types

  SOMCalloc          calloc          void *   size_t, size_t
  SOMFree            free            void     void *
  SOMMalloc          malloc          void *   size_t
  SOMRealloc         realloc         void *   void *, size_t

Table 1 - Memory-Management Functions
```

Note:  Generally speaking, all of these routines should be replaced as a unit. That is, if you wish to supply your own version of SOMMalloc that did all of its allocations as suballocations in a shared memory heap (for instance), you also should supply corresponding SOMCalloc, SOMFree, and SOMRealloc functions that conformed to this same style of memory management.


### DLL Management Functions

The SOM run time uses three routines to manage the loading and unloading of DLLs. You can modify the rules that govern the loading and unloading of DLLs by replacing these functions with alternative implementations. 

SOMClassInitFuncName 

```
  zString (*SOMClassInitFuncName) (void);
```

This function returns the name of the function that will initialize all of the classes that are packaged together in a single DLL. The SOM-supplied version of this function returns the string "SOMInitModule." Hence, unless you supply your own alternative to this function, in order to package more than one SOM class in a single OS/2* DLL, you should write a C-language function named "SOMInitModule" that initializes each class in the DLL. For example, if you wanted to create a DLL that had three classes (A, B, and C), your SOMInitModule function would look something like this: 

```
  #include <a.h>
  #include <b.h>
  #include <c.h>
  #pragma linkage (SOMInitModule, system)
  void SOMInitModule (integer4 majorVersion, integer4 minorVersion)
      {
      ANewClass (1,0); /* Pass major and minor version numbers */
      BNewClass (2,1); /*  appropriate to each class           */
      CNewClass (majorVersion, minorVersion);
      }
```

Be sure to include SOMInitModule as an exported entry point in your .DEF file when creating your DLL. 

SOMDeleteModule 

```
  int (*SOMDeleteModule) (IN somToken modHandle);
```

This function deletes the DLL designated by the value of the parameter, modHandle, and returns 0 for success or a non-zero system-specific error code. The parameter, modHandle, contains a value returned from SOMLoadModule (the DLL loading routine). The default version of this function supplied with SOM returns the OS/2* module handle for the loaded DLL. The default SOMDeleteModule routine uses this DLL module handle to invoke the OS/2* 2.0 DosFreeModule function. The result is used as the return value. 

SOMLoadModule 

```
  int (*SOMLoadModule) (IN zString className,
          IN zString fileName,
          IN zString functionName,
          IN integer4 majorVersion,
          IN integer4 minorVersion,
          OUT somToken *modHandle);
```

This function should load the DLL containing the SOM class className and return the value 0 for success or a non-zero system-specific error code. The output argument modHandle should be used to return a token that can be subsequently used by the SOMDeleteModule routine to unload the DLL. The default SOMLoadModule routine supplied with SOM passes back the OS/2* DLL module handle in this argument. The remaining arguments are used as follows: 

Argument Usage 

fileName This argument has the DLL file name, suitable for use with the OS/2* 2.0 DosLoadModule function. It can be either a simple name or a fully qualified name. 

functionName This is the name of the routine to be called if the DLL can be successfully loaded. This routine is responsible for creating the SOM class or classes contained in the DLL. Typically this argument will have the value "SOMInitModule" obtained from SOMClassInitFuncName described above. If no "SOMInitModule" entry exists in the DLL, the default version of SOMLoadModule looks for a routine with the name <className>NewClass instead. If neither entry point can be found the SOMLoadModule function will fail. 

majorVersion The major version number should be passed to the class initialization function in the DLL. 

minorVersion The minor version number should be passed to the class initialization function in the DLL.


### Character Output Function

This routine is invoked from the SOM run-time environment whenever a character is generated by one of the SOM error-handling or debugging macros. The default version of this routine supplied with SOM simply writes the character to stdout and returns a 1, if successful, or a 0 if not. You might wish to supply a replacement routine to: 

oDirect the output to stderr 

oRecord the output in a log file 

oCollect characters and handle them in larger chunks 

oSend the output to a PM window to display it 

oPlace the output in the PM clipboard 

oOr some combination of these 

Use a coding construct similar to the following to install your replacement routine. 

```
    #include <som.h>
    /* Define your replacement routine */
    int myReplacementForSOMOutChar (char c)
    {
        (Your code goes here)
    }
    ...
    /* After the next stmt all output */
    /* will be sent to your routine   */
    SOMOutCharRoutine = myReplacementForSOMOutChar;
```


### Error-Handling Function

SOMError 

```
  void (*SOMError)(int errorCode, zString fileName, int lineNum);
```

This function inspects the errorCode argument and takes appropriate action. The last decimal digit of errorCode indicates whether the classification of the error is SOM_Fatal, SOM_Warn, or SOM_Ignore (see Error-Handling Facilities for a discussion of error classifications). In the default SOMError fatal errors will end the current process. The remaining two arguments (fileName and lineNum) indicate the name of the file and the line number within the file where the error was detected. 

All error conditions that originate within the classes supplied as part of the SOM run time, leave SOM in an internally consistent state. If you wish to trap them with your error-handling function and resume with some other type of processing, you can do so knowing that all of the methods supplied with SOM behave atomically. That is, they either complete or fail, but if they fail, partial effects are backed out wherever possible so that all SOM methods remain useable and can be re-executed. 

Within your own error-handling function you may wish to: 

oRecord errors in a way appropriate to your application. 

oInform the user through your application's user interface. 

oAttempt application level recovery by restarting at a known point. 

oShut down your particular application.


## Classes Reference


### SOMObject

Class: SOMObject 

Parent: <none> 

Metaclass: SOMClass 

File stem SOMOBJ 

Definition: SOMOBJ.SC 

Header file: SOMOBJ.H (always included from SOM.H) 

Description: SOMObject is the root class for all SOM classes. It defines the essential behavior common to all SOM objects. As SOMObject has no instance data, it contributes nothing to the size of derived classes. 

Notes on subclassing: All SOM classes are expected to derive from SOMObject. Three methods would typically be overridden by any subclass that has instance data-somInit, somUninit, and somDumpSelfInt. See the descriptions of these methods for further information. 

New methods: [Initialization/Termination Group] 

somFree 
somInit 
somUninit 

[Access Group] 

somGetClass 
somGetClassName 
somGetSize 

[Testing Group] 

somIsA 
somIsInstanceOf 
somRespondsTo 

[Dynamic Group] 

somDispatchA 
somDispatchD 
somDispatchL 
somDispatchV 

[Development Support Group] 

somDumpSelf 
somDumpSelfInt 
somPrintSelf 

Inherited methods: None 

Overridden methods: None


### SOMClass

Class: SOMClass 

Parent: SOMObject 

Metaclass: SOMClass (only class with itself as metaclass) 

File stem SOMCLS 

Definition: SOMCLS.SC 

Header file: SOMCLS.H (always included from SOM.H) 

Description: SOMClass is the root class for all SOM metaclasses. It defines the essential behavior common to all SOM classes, In particular, it has two generic methods for manufacturing object instances (somNew and somRenew), and a suite of methods for constructing classes. It also has methods that can be used to dynamically obtain (or augment) information about a class and its methods at run time. 

Notes on subclassing: All SOM classes are expected to have SOMClass or a class derived from SOMClass as their metaclass.  Metaclasses define "class" methods (sometimes called "factory" methods or "constructors") that can be used to manufacture objects of any class for which they are the metaclass.  If you wish to define your own class methods for your objects, or impart specialized behavior to the generic class methods supplied in SOMClass, you will need to define your own metaclass by subclassing SOMClass or one of its other subclasses.  Three methods that SOMClass inherits and overrides from SOMObject would typically be overridden by any metaclass that has instance data - somInit, somUninit, and somDumpSelfInt.  See the descriptions of these methods in SOMObject for further information.  The new methods introduced in SOMClass that might frequently be overridden are somNew, somNewNoInit, somRenew, somRenewNoInit, and somClassReady. 

Other reasons that you may want to create your own metaclass include tracking object instances, automatic garbage collection, interfacing to a persistent object store, or providing/managing information that is global to a set of object instances. 

New methods: [Initialization/Termination Group] 

somAddStaticMethod 
somClassReady 
somInitClass 
somOverrideSMethod 

[Instance Creation (Factory) Group] 

somNew 
somNewNoInit 
somRenew 
somRenewNoInit 

[Access Group] 

somGetApplyStub 
somGetClassData 
somGetClassMtab 
somGetInstanceOffset 
somGetInstancePartSize 
somGetInstanceSize 
somGetName 
somGetNumMethods 
somGetNumStaticMethods 
somGetParent 
somGetPClsMtab 
somSetClassData 

[Testing Group] 

somCheckVersion 
somDescendedFrom 
somSupportsMethod 

[Dynamic Group] 

somFindMethod 
somFindMethodOk 

Inherited methods: somDispatchA 
somDispatchD 
somDispatchL 
somDispatchV 
somDumpSelf 
somFree 
somGetClassName 
somGetClass 
somGetSize 
somIsA 
somIsInstanceOf 
somPrintSelf 
somRespondsTo 

Overridden methods: somDumpSelfInt 
somInit 
somUninit


### SOMClassMgr

Class: SOMClassMgr 

Parent: SOMObject 

Metaclass: SOMClass 

File stem SOMCM 

Definition: SOMCM.SC 

Header file: SOMCM.H (always included from SOM.H) 

Description: One instance of SOMClassMgr is created during SOM initialization. It acts as a run-time registry for all SOM class objects that have been created or dynamically loaded by the current process. Each SOM class automatically registers itself with the SOMClassMgr instance (pointed to by the global variable, SOMClassMgrObject) during the final stage of its initialization. 

Notes on subclassing: You can subclass SOMClassMgr to augment the functionality of its registry (to make it persistent, for example, or to coordinate the name of a class with the location of its code in the file system).  If you want your subclass to replace the SOM-supplied SOMClassMgrObject, you can use the somMergeInto method to place the existing registry information from SOMClassMgrObject into your new class-manager object as a final step in the creation of an instance of your subclass. The former SOMClassMgrObject is then freed, and the address of your new class manager is placed in this global variable. 

New methods: [Basic Functions Group] 

somLoadClassFile 
somLocateClassFile 
somRegisterClass 
somUnloadClassFile 
somUnregisterClass 

[Access Group] 

somGetInitFunction 

[Dynamic Group] 

somClassFromId 
somFindClass 
somFindClsInFile 
somMergeInto 

Inherited methods: somDispatchA 
somDispatchD 
somDispatchL 
somDispatchV 
somDumpSelf 
somFree 
somGetClass 
somGetClassName 
somGetSize 
somIsA 
somIsInstanceOf 
somPrintSelf 
somRespondsTo 

Overridden methods: somDumpSelfInt 
somInit 
somUninit


## Methods Reference


### somAddStaticMethod


### Instructions *(hidden)*

Topics: 

Call Syntax 
Uses 
Parameters 
Return Value 
Errors 
Notes 
Related Methods 
Example 
Glossary


### Call Syntax *(hidden)*

/* Class:  SOMClass
  *Method :somAddStaticMethod
  *
  *Addastaticmethodtoaclassor
  *overrideaparentstaticmethod
  * / 
  #include <som.h>
  SOMClass* receiver ; 
  somId methodId;
  zStringmethodDescriptor ; 
  somMethodProc *method;
  somMethodProc* redispatchStub ; 
  somMethodProc *applyStub;
  intoffset ; 
  offset = _somAddStaticMethod (receiver,
                 methodId , 
                 methodDescriptor,
                 method ,redispatchStub , 
                 applyStub);


### Uses *(hidden)*

Adds or overrides the indicated method to the receiving class. The somAddStaticMethod method is used by the procedure that constructs the SOM class object.


### Parameters *(hidden)*

receiver The SOM class that should add this (static) method. 

methodId A somId that represents the name of this method. 

methodDescriptor A string that describes the types of arguments and the returned value (if any) associated with this method. 

method The actual method procedure for this method. 

redispatchStub A procedure with the same calling sequence as this method that re-dispatches the method to one of this class's dispatch functions. 

applyStub A procedure that applies a standard data structure for a variable argument list to its target object by calling this method with arguments derived from the data structure.  Its calling sequence is the same as that of the dispatch methods defined in SOMObject.  This stub supports the dispatch methods used in some classes. In classes where the dispatch functions do not need such a function, this parameter can be null.


### Return Value *(hidden)*

The offset into the class's static method table for this method is returned.  This value can be used subsequently as an index for offset method resolution.


### Notes *(hidden)*

In general, C-language programmers do not need to use this method, because the SOM Compiler generates all of the code to construct a class in the .IH file for the class.


### Related Methods *(hidden)*

somInitClass 
somOverrideSMethod


### Example *(hidden)*

```
   /* New Method: newMethod1 */

   void newMethod1(XXX *somSelf, int arg1);
   static char *somMN_newMethod1 = "newMethod1";
   static somId somId_newMethod1 = &somMN_newMethod1;
   static void  somRD_newMethod1(XXX *somSelf, int arg1)
   {
      va_somDispatchV(somSelf, somId_newMethod1,
              somMD_XXX_newMethod1,arg1);
   }
   static void somAP_newMethod1(XXX *somSelf, somId id,
              char *desc, va_list ap)
   {
      int arg1 = va_arg(ap, int);
      _newMethod1(somSelf,arg1);
   }

   XXXClassData.newMethod1 = (integer2)
     _somAddStaticMethod (XXXClassData.classObject,
           somId_newMethod1,
           somMD_XXX_newMethod1,
           (somMethodProc *) newMethod1,
           (somMethodProc *) somRD_newMethod1,
           (somMethodProc *) somAP_newMethod1);
```


### somCheckVersion


### Instructions *(hidden)*

Topics: 

Call Syntax 
Uses 
Parameters 
Return Value 
Errors 
Notes 
Related Methods 
Example 
Glossary


### Call Syntax *(hidden)*

/* Class:  SOMClass
  *Method :somCheckVersion
  *
  *Checktoseethataclassiscompatible
  *withthespecifiedversioninformation . 
  */
  # include< som . h > 
  SOMClass *receiver;
  integer4majorVersion ; 
  integer4 minorVersion;
  intresult ; 
  result = _somCheckVersion (receiver,
               majorVersion , 
               minorVersion);


### Uses *(hidden)*

Check the receiving class for compatibility with the specified major and minor version numbers. An implementation is compatible with the specified version numbers if it has the same major version number and a minor version number that is equal to or greater than minorVersion. The major, minor version number pair (0,0) is considered to match any version.


### Parameters *(hidden)*

receiver The SOM class whose version information should be checked. 

majorVersion This value usually changes only when a significant enhancement or incompatible change is made to a class. 

minorVersion This value changes whenever minor enhancements or fixes are made to a class.  Downward compatibility is generally maintained across changes in the minorVersion number.


### Return Value *(hidden)*

Returns 1 (true) if the implementation of this class is compatible with the specified major and minor version number, and false (0) if otherwise.


### Notes *(hidden)*

This method is usually called immediately after creating the class object to verify that a dynamically loaded class definition is compatible with a using application.


### Related Methods *(hidden)*

somInitClass


### Example *(hidden)*

```
   #include "animal.h"
   main()
   {
     Animal *myAnimal;
     myAnimal = AnimalNew();

     if (_somCheckVersion(_Animal, 0, 0))
        somPrintf("Animal IS compatible with 0.0\n");
     else
        somPrintf("Animal IS NOT compatible with 0.0\n");

     if (_somCheckVersion(_Animal, 1, 1))
        somPrintf("Animal IS compatible with 1.1\n");
     else
        somPrintf("Animal IS NOT compatible with 1.1\n");
   }
   /*
   Output from this program:

   Animal IS compatible with 0.0
   Animal IS NOT compatible with 1.1
   */
```


### somClassFromId


### Instructions *(hidden)*

Topics: 

Call Syntax 
Uses 
Parameters 
Return Value 
Errors 
Notes 
Related Methods 
Example 
Glossary


### Call Syntax *(hidden)*

/* Class:  SOMClassMgr
  *Method :somClassFromId
  *
  *Findaclass ,givenitsID
  * / 
  #include <som.h>
  SOMClassMgr* receiver ; 
  somId classId;
  SOMClass* class ; 
  class = _somClassFromId (receiver, classId);


### Uses *(hidden)*

Finds the class object, given its ID, if it already exists. Does not load the class.


### Parameters *(hidden)*

receiver Usually SOMClassMgrObject (or an instance of a user-supplied subclass of SOMClassMgr). 

classId The ID to use as a key to find the class.


### Return Value *(hidden)*

Returns NULL if the class object does not yet exist; otherwise, a pointer to the class is returned.


### Notes *(hidden)*

Use this method instead of somFindClass when you do NOT wish the class to be automatically loaded if it does not already exist in the current process.


### Related Methods *(hidden)*

somFindClass 
somFindClsInFile


### Example *(hidden)*

```
    # include   " som . h " 

    SOMClass   * myClass ; 
    char   * myClassName   =   " SampleClass " ; 

    myClass   =   _ somClassFromId ( SOMClassMgrObject , 
                                SOM _ IdFromString ( myClassName ) ) ; 
    if   ( ! myClass ) 
        somPrintf ( " Class   % s   has   not   yet   been   loaded . \ n " ,   myClassName ) ; 
```


### somClassReady


### Instructions *(hidden)*

Topics: 

Call Syntax 
Uses 
Parameters 
Return Value 
Errors 
Notes 
Related Methods 
Glossary


### Call Syntax *(hidden)*

/* Class:  SOMClass
  *Method :somClassReady
  *
  *Indicatethataclasshasbeenconstructed
  *andisreadyfornormaluse . 
  */
  # include< som . h > 
  SOMClass *receiver;
  _ somClassReady( receiver ) ;


### Uses *(hidden)*

This method is invoked when all of the static initialization for the class is finished.  The default implementation simply registers the newly constructed class with SOMClassMgrObject. Metaclasses can override this method to augment the class construction sequence in any way that they wish.


### Parameters *(hidden)*

receiver The class object that has just been constructed.


### Return Value *(hidden)*

None.


### Notes *(hidden)*

If you have special processing to do when your class is first created, you can define a metaclass for your class that overrides this method. Typically, the final statement in any overriding method is parent_somClassReady (somSelf) to ensure that your class is properly registered with SOMClassMgrObject. 

Never invoke this method yourself; it is invoked automatically at the appropriate time during class construction.


### Related Methods *(hidden)*

somInitClass


### somDescendedFrom


### Instructions *(hidden)*

Topics: 

Call Syntax 
Uses 
Parameters 
Return Value 
Errors 
Notes 
Related Methods 
Example 
Glossary


### Call Syntax *(hidden)*

/* Class:  SOMClass
  *Method :somDescendedFrom
  *
  *Testwhetherthereceivingclassisderived
  *fromthespecifiedclass . 
  */
  # include< som . h > 
  SOMClass *receiver;
  SOMClass* aClassObj ; 
  int result = _somDescendedFrom (receiver, aClassObj);


### Uses *(hidden)*

For programs that use classes as types, this method can be used to ascertain if the type of an object is a subtype of another.


### Parameters *(hidden)*

receiver The class object to be tested. 

aClassObj The potential ancestor class.


### Return Value *(hidden)*

Returns 1 (true) if the receiving class is a descendent class of the argument class, and 0 (false) if otherwise.


### Notes *(hidden)*

A class object is considered to be descended from itself for the purpose of this method.


### Related Methods *(hidden)*

somIsA 
somIsInstanceOf


### Example *(hidden)*

```
#include "animal.h"
#include "dog.h"
/* ---------------------------------------------------
   Note: Dog is a subclass of Animal.
   --------------------------------------------------- */
main()
{
  AnimalNewClass(1,1);
  DogNewClass(1,1);

  if (_somDescendedFrom (_Dog, _Animal))
     somPrintf("dog IS descended from animal\n");
  else
     somPrintf("dog is NOT descended from animal\n");
  if (_somDescendedFrom (_Animal, _Dog))
     somPrintf("animal IS descended from dog\n");
  else
     somPrintf("animal is NOT descended from dog\n");
}
/*
Output from this program:
dog IS descended from animal
animal is NOT descended from dog
*/
```


### somDispatchX


### Instructions *(hidden)*

Topics: 

Call Syntax 
Uses 
Parameters 
Return Value 
Errors 
Notes 
Related Methods 
Example 
Glossary


### Call Syntax *(hidden)*

/* Class:  SOMObject
  *Method :somDispatch X 
  * 
  * Invoke a method using a dispatch mechanism.
  * / 
  #include <som.h>
  SOMAny* receiver ; 
  somId  methodId;
  somId descriptor ; 
  void *ptr;
  float8rnum ; 
  integer4 inum;
  ptr =_ somDispatchA( receiver ,methodId ,descriptor ,. . . ) ; 
  rnum = _somDispatchD (receiver, methodId, descriptor, ...);
  inum=_ somDispatchL( receiver ,methodId ,descriptor ,. . . ) ; 
      _somDispatchV (receiver, methodId, descriptor, ...);


### Uses *(hidden)*

The somDispatchX methods are used to invoke a designated method using a dispatching algorithm appropriate for the class of the specified receiving object. The actual object that will receive the designated method is determined by the particular dispatching algorithm associated with the class. 

All SOM objects permit the use of a dispatch mechanism to perform method resolution for any method. The default dispatch algorithm supplied in the SOMObject class always selects the specified receiving object as the target of the call and invokes the "apply stub" for the designated method.


### Parameters *(hidden)*

receiver The object that represents the context in which the dispatch method resolution will occur. 

methodId An ID that represents the name of the method to be dispatched. 

descriptor An ID that represents a string that describes the arguments (and their types) associated with the target method. 

... The remaining arguments are any that are needed for the method to be dispatched.


### Return Value *(hidden)*

Four families of return values are supported, corresponding to the four forms of the somdispatchX method. Within each of the four families, only the largest representation is supported. The four families are: 

Pointer This type of result is returned from somDispatchA. It can be cast to be a pointer to a specific type appropriate for the method that is being dispatched. 

Floating point This result is returned from somDispatchD as a float8. 

Integer This result is returned from somDispatchL as an integer4. 

Void somDispatchV is used for any method that does not return a result.


### Notes *(hidden)*

These methods make it easier for dynamic domains to bind to the SOM-object protocol boundary. In addition, they determine the appropriate method procedure, then call it with the arguments specified. The default implementations of these methods provided in this class simply look up the apply stub associated with the method and call it. However, other classes can choose to implement any form of lookup they wish. For example, one could provide an implementation of these methods that used the CLOS (Common Lisp Object System) form of method resolution. For domains that can do so, it generally will be much faster to invoke their methods directly rather than going through a dispatch method. However, all methods can be reached through the dispatch methods. 

These methods are declared to take a variable-length argument list, but as with all such methods, SOM requires that the variable part of the argument list be assembled into the standard data structure for variable argument lists before the method is actually invoked. This can be very useful in domains that need to construct the argument list at run time, because they can invoke methods without being able to put the constructed arguments in the normal form for a call. Usually such an operation is impossible in most high-level languages, and the use of assembler language routines would otherwise be necessary.


### Related Methods *(hidden)*

somGetApplyStub


### Example *(hidden)*

```
#include "animal.h"
void main()
{
   Animal *myAnimal;
   char *myNoise = "Roar!!!";
   somId somId_setSound;

   myAnimal = AnimalNew();
/* --------------------------------------
   Note: Next two lines are equivalent to
   _setSound(myAnimal, myNoise);
   -------------------------------------- */
   somId_setSound = SOM_IdFromString("setSound");
   _somDispatchV(myAnimal, somId_setSound , (void *) 0, &myNoise);

   _display(myAnimal);
   _somFree(myAnimal);
}
/*
Program Output:
This Animal says
Roar!!!
*/
```


### somDumpSelf


### Instructions *(hidden)*

Topics: 

Call Syntax 
Uses 
Parameters 
Return Value 
Errors 
Notes 
Related Methods 
Example 
Glossary


### Call Syntax *(hidden)*

/* Class:  SOMObject
  *Method :somDumpSelf
  *
  *Writesadetaileddescriptionofthereceiving
  *objectto( * SOMOutCharRoutine ) ( char ) ; 
  */
  # include< som . h > 
  SOMAny *receiver;
  intlevel ; 
  _somDumpSelf (receiver, level);


### Uses *(hidden)*

Uses SOMOutCharRoutine to write a detailed description of this object and its current state. The default implementation produces a header line identifying the receiving object and its class, then invokes somDumpSelfInt to format any instance data in the object.


### Parameters *(hidden)*

receiver The object to be dumped. 

level The nesting level for describing compound objects. It must be greater than or equal to 0. All lines in the description will be preceded by "2 X level" spaces.


### Return Value *(hidden)*

None.


### Notes *(hidden)*

This routine writes only the data that concerns the object as a whole, such as class, and uses somDumpSelfInt to describe the object's current state. This approach allows readable descriptions of compound objects to be constructed. 

Generally, it is not necessary to override this method, but if it IS overridden it typically will need to be replaced completely.


### Related Methods *(hidden)*

somDumpSelfInt 
somPrintSelf


### Example *(hidden)*

```
#include "animal.h"
main()
{
  Animal *myAnimal;
  myAnimal = AnimalNew();
  /* ... */
  _somDumpSelf(myAnimal, 0);
}
```


### somDumpSelfInt


### Instructions *(hidden)*

Topics: 

Call Syntax 
Uses 
Parameters 
Return Value 
Errors 
Notes 
Related Methods 
Glossary


### Call Syntax *(hidden)*

/* Class:  SOMObject
  *Method :somDumpSelfInt
  *
  *Writestheinternalstateofthereceiving
  *objectto( * SOMOutCharRoutine ) ( char ) ; 
  */
  # include< som . h > 
  SOMAny *receiver;
  intlevel ; 
  _somDumpSelfInt (receiver, level);


### Uses *(hidden)*

somDumpSelf invokes this method to write out the instance data stored in the receiving object. The default implementation does nothing (SOMObject has no instance data). Overriding methods can use SOMOutCharRoutine to write instance data in a readable format to the SOM output destination.


### Parameters *(hidden)*

receiver The object to be dumped. 

level The nesting level for describing compound objects. It must be greater than or equal to 0. All lines in the description will be preceded by "2 X level" spaces.


### Return Value *(hidden)*

None.


### Notes *(hidden)*

Uses (*SOMOutCharRoutine)() to write out the current state of this object. If your class has instance data, override this method. Begin by calling the parent class form of this method, then write out a description of your class's instance data. This will result in a description of all the object's instance data, from its root ancestor class to its specific class. 

This method generally is not invoked directly. Use somDumpSelf instead, which will invoke somDumpSelfInt.


### Related Methods *(hidden)*

somDumpSelf 
somPrintSelf


### somFindClass


### Instructions *(hidden)*

Topics: 

Call Syntax 
Uses 
Parameters 
Return Value 
Errors 
Notes 
Related Methods 
Example 
Glossary


### Call Syntax *(hidden)*

/* Class:  SOMClassMgr
  *Method :somFindClass
  *
  *FindstheclassobjectwhengivenitsID . 
  * If the class does not exist, dynamically 
  * loads it.
  * / 
  #include <som.h>
  SOMClassMgr* receiver ; 
  somId classId;
  intmajorVersion ; 
  int minorVersion;
  SOMClass* class ; 
  class = _somFindClass (receiver, classId, majorVersion, minorVersion);


### Uses *(hidden)*

Returns the class object for the specified class.  This may result in dynamic loading.  This method first uses somLocateClassFile to obtain the name of the file where the class' code resides, then uses somFindClsInFile.


### Parameters *(hidden)*

receiver Usually SOMClassMgrObject (or an instance of a user-supplied subclass of SOMClassMgr). 

classId The ID to use as a key to find the class. 

majorVersion The class's major version number. 

minorVersion The class's minor version number. 

If majorVersion and minorVersion are not both zero, they are used to check the class version information against the caller's expectations.


### Return Value *(hidden)*

A pointer to the requested class object, or NULL if the class could not be created.


### Notes *(hidden)*

If the requested class has not yet been created this routine will attempt to load the class dynamically by loading its .DLL and invoking its "new class" procedure.


### Related Methods *(hidden)*

somFindClsInFile 
somLocateClassFile


### Example *(hidden)*

```
#include "animal.h"

void main()
{
   Animal *bigAnimal;
   SOMClass *myClass;
   char *animalName = "Animal";

   bigAnimal = AnimalNew();
   myClass = _somFindClass (SOMClassMgrObject,
                            SOM_IdFromString(animalName),
                            0, 0);
   somPrintf("myClass: %s\n", _somGetName(myClass));
   _somFree(bigAnimal);
}
/*
Output from this program:
myClass: Animal
*/
```


### somFindClsInFile


### Instructions *(hidden)*

Topics: 

Call Syntax 
Uses 
Parameters 
Return Value 
Errors 
Notes 
Related Methods 
Example 
Glossary


### Call Syntax *(hidden)*

/* Class:  SOMClassMgr
  *Method :somFindClsInFile
  *
  *SameassomFindClass ,exceptthecallerprovidesthe
  *filenametobeusedifdynamicloadingisneeded . 
  * 
  */
  # include< som . h > 
  SOMClassMgr *receiver;
  somIdclassId ; 
  int majorVersion;
  intminorVersion ; 
  zString file;
  SOMClass* class ; 
  class = _somFindClsInFile (receiver, classId, majorVersion, minorVersion, file);


### Uses *(hidden)*

Returns the class object for the specified class.  This can result in dynamic loading.  This method uses the passed parameter file as the name of the .DLL containing the class.


### Parameters *(hidden)*

receiver Usually SOMClassMgrObject (or an instance of a user-supplied subclass of SOMClassMgr). 

classId The ID to use as a key to find the class. 

majorVersion The class's major version number. 

minorVersion The class's minor version number. 

file The name of the .DLL file containing the class. 

If majorVersion and minorVersion are not both zero, they are used to check the class version information against the caller's expectations.


### Return Value *(hidden)*

A pointer to the requested class object, or NULL if the class could not be loaded and created.


### Notes *(hidden)*

If the requested class has not yet been created this routine will attempt to load the class dynamically by loading its .DLL and invoking its "new class" procedure.


### Related Methods *(hidden)*

somFindClass


### Example *(hidden)*

```
#include "som.h"
/*
 *  This program loads a class and creates
 *  an instance of it without having any
 *  external references to it.
 *
 */
void main()
{
   SOMAny *myAnimal;
   SOMClass *animalClass;
   char *animalName = "Animal";
   char *animalFile = "C:\\MYDLLS\\ANIMAL.DLL";

   animalClass = _somFindClsInFile (SOMClassMgrObject,
                                    SOM_IdFromString(animalName),
                                    0, 0,
                                    animalFile);
   myAnimal = _somNew (animalClass);
   somPrintf("The class of myAnimal is %s.\n",
       _somGetClassName(myAnimal));
   _somFree(myAnimal);
}
/*
Output from this program:
The class of myAnimal is Animal.
*/
```


### somFindMethod


### Instructions *(hidden)*

Topics: 

Call Syntax 
Uses 
Parameters 
Return Value 
Errors 
Notes 
Related Methods 
Example 
Glossary


### Call Syntax *(hidden)*

/* Class:  SOMClass
  *Method :somFindMethod
  *
  *GivenamethodId ,returnsaprocedureaddress
  *andanindicationofwhetheritrepresents
  *adirectmethodcalloradispatchingfunction . 
  */
  # include< som . h > 
  SOMClass *receiver;
  somIdmethodId ; 
  somMethodProc **m;
  intdirectFlag ; 
  directFlag = _somFindMethod (SOMClass *receiver, methodId, m);


### Uses *(hidden)*

Finds the method procedure associated with methodId for the receiving class and sets *m to it.


### Parameters *(hidden)*

receiver The class object whose method is desired. 

methodId An ID that represents the name of the desired method. 

m A pointer to a pointer to a somMethodProc. *m is set either to NULL (if the method does not exist), or to a value that can be called.


### Return Value *(hidden)*

Returns 1 (true) when the method procedure can be called directly, and 0 (false) when the method procedure is a dispatch function.


### Notes *(hidden)*

If the class does not support the specified method, then *m is set to NULL and the return value is meaningless. Returning a dispatch function does not guarantee that a class supports the specified method; the dispatch might fail. 

If a dispatch function is returned (directFlag == 0) the calling sequence is slightly different than that for a direct method; two additional parameters are required-methodId and descriptorId.


### Related Methods *(hidden)*

somFindMethodOk 
somSupportsMethod


### Example *(hidden)*

```
#include "animal.h"
void main()
{
   Animal *myAnimal;
   somId somId_setSound;
   somMethodPtr methodPtr;
   myAnimal = AnimalNew();
/* ----------------------------------------
   Note: Next three lines are equivalent to
       _setSound(myAnimal, "Roar!!!");
   ---------------------------------------- */
   somId_setSound = SOM_IdFromString("setSound");
   _somFindMethod (_somGetClass(myAnimal),
                   somId_setSound, &methodPtr);
   methodPtr(myAnimal, "Roar!!!");
/* ---------------------------------------- */
   _display(myAnimal);
   _somFree(myAnimal);
}
/*
Program Output:
This Animal says
Roar!!!
*/
```


### somFindMethodOk


### Instructions *(hidden)*

Topics: 

Call Syntax 
Uses 
Parameters 
Return Value 
Errors 
Notes 
Related Methods 
Example 
Glossary


### Call Syntax *(hidden)*

/* Class:  SOMClass
  *Method :somFindMethodOk
  *
  *GivenamethodId ,returnsaprocedureaddress
  *andanindicationofwhetheritrepresents
  *adirectmethodcalloradispatchingfunction . 
  */
  # include< som . h > 
  SOMClass *receiver;
  somIdmethodId ; 
  somMethodProc **m;
  intdirectFlag ; 
  directFlag = _somFindMethodOk (SOMClass *receiver, methodId, m);


### Uses *(hidden)*

Finds the method procedure associated with methodId for the receiving class and sets *m to it. If methodId is not supported, an error is raised and execution is halted.


### Parameters *(hidden)*

receiver The class object whose method is desired. 

methodId An ID that represents the name of the desired method. 

m A pointer to a pointer to a somMethodProc. *m is set either to NULL (if the method does not exist), or to a value that can be called.


### Return Value *(hidden)*

Returns 1 (true) when the method procedure can be called directly, and 0 (false) when the method procedure is a dispatch function.


### Notes *(hidden)*

If the class does not support the specified method then *m is set to NULL and the return value is meaningless. Returning a dispatch function does not guarantee that a class supports the specified method; the dispatch might fail. 

If a dispatch function is returned (directFlag == 0), the calling sequence is slightly different than that of a direct method; two additional parameters are required-methodId and descriptorId.


### Related Methods *(hidden)*

somFindMethod 
somSupportsMethod


### Example *(hidden)*

```
#include "animal.h"
void main()
{
   Animal *myAnimal;
   somId somId_setSound;
   somMethodPtr methodPtr;
   myAnimal = AnimalNew();
/* ----------------------------------------
   Note: Next three lines are equivalent to
       _setSound(myAnimal, "Roar!!!");
   ---------------------------------------- */
   somId_setSound = SOM_IdFromString("setSound");
   _somFindMethodOk (_somGetClass(myAnimal),
                     somId_setSound, &methodPtr);
   methodPtr(myAnimal, "Roar!!!");
/* ---------------------------------------- */
   _display(myAnimal);
   _somFree(myAnimal);
}
/*
Program Output:
This Animal says
Roar!!!
*/
```


### somFree


### Instructions *(hidden)*

Topics: 

Call Syntax 
Uses 
Parameters 
Return Value 
Errors 
Notes 
Related Methods 
Example 
Glossary


### Call Syntax *(hidden)*

/* Class:  SOMObject
  *Method :somFree
  *
  *Releasethestorageusedbythereceiver
  *andfreetheobject . 
  */
  # include< som . h > 
  SOMAny *receiver;
  _ somFree( receiver ) ;


### Uses *(hidden)*

Releases the storage associated with the receiving object, assuming that it was created originally by somNew or somNewNoInit (or another class method that used either of these methods to allocate its objects). No future references should be made to the receiving object. This method calls somUninit before releasing storage.


### Parameters *(hidden)*

receiver The object to be freed.


### Return Value *(hidden)*

None.


### Notes *(hidden)*

This method must be called only on objects that were originally created by somNew (or somNewNoInit), and never on objects created by somRenew (or somRenewNoInit). It is not necessary to override this method (override somUninit instead).


### Related Methods *(hidden)*

somNew 
somNewNoInit 
somRenew 
somRenewNoInit 
somUninit


### Example *(hidden)*

```
#include "animal.h"

void main()
{
   Animal *myAnimal;
   /*
    * Create an object.
    */
   myAnimal = AnimalNew();

   /* ... */

   /*
    * Free it when finished.
    */
   _somFree(myAnimal);
}
```


### somGetApplyStub


### Instructions *(hidden)*

Topics: 

Call Syntax 
Uses 
Parameters 
Return Value 
Errors 
Notes 
Related Methods 
Example 
Glossary


### Call Syntax *(hidden)*

/* Class:  SOMClass
  *Method :somGetApplyStub
  *
  *Obtaintheapplystubforagivenmethod
  * / 
  #include <som.h>
  SOMClass* receiver ; 
  somId methodId;
  somMethodProc* applyStub ; 
  applyStub = _somGetApplyStub (receiver, methodId);


### Uses *(hidden)*

This method returns the address of an "apply stub" for the indicated method.  An apply stub is a special procedure that accepts the arguments for a particular method in the form of a standard varargs data structure.  It extracts the arguments, then invokes the method, subsequently returning its result to the original caller. Apply stubs are useful in situations when a static method invocation cannot be constructed at compile time.


### Parameters *(hidden)*

receiver The class object whose method is desired. 

methodId An ID that represents the name of the desired method.


### Return Value *(hidden)*

Returns the apply stub associated with the specified method. NULL is returned if the method is not supported by this class.


### Notes *(hidden)*

The calling sequence for any apply stub is shown below. 

```
    #include <stdarg.h>

    somMethodProc *applyStub;
    SOMAny *receiver;
    somId methodId;
    somId descriptor;
    va_list arglist;
    resultType result;

    result = (*applyStub)(receiver, methodId, descriptor, arglist);
```


### Related Methods *(hidden)*

None.


### Example *(hidden)*

```
#include "animal.h"
void main()
{
   Animal *myAnimal;
   char *myNoise = "Roar!!!";
   somId somId_setSound;
   somMethodPtr applyStub;

   myAnimal = AnimalNew();
/* ----------------------------------------
   Note: Next three lines are equivalent to
       _setSound(myAnimal, myNoise);
   ---------------------------------------- */
   somId_setSound = SOM_IdFromString("setSound");
   applyStub = _somGetApplyStub(
      _somGetClass(myAnimal), somId_setSound);
   applyStub (myAnimal, somId_setSound , (void *) 0, &myNoise);
/* ---------------------------------------- */
   _display(myAnimal);
   _somFree(myAnimal);
}
/*
Program Output:
This Animal says
Roar!!!
*/
```


### somGetClass


### Instructions *(hidden)*

Topics: 

Call Syntax 
Uses 
Parameters 
Return Value 
Errors 
Notes 
Related Methods 
Example 
Glossary


### Call Syntax *(hidden)*

/* Class:  SOMObject
  *Method :somGetClass
  *
  *Getapointertoanobject ' sclassobject
  * / 
  #include <som.h>
  SOMAny* receiver ; 
  SOMClass *class;
  class=_ somGetClass( receiver ) ;


### Uses *(hidden)*

Obtain a pointer to the receiver's class object.


### Parameters *(hidden)*

receiver is the object whose class is desired.


### Return Value *(hidden)*

A pointer to the object's class object is returned.


### Notes *(hidden)*

A slightly faster macro form of this method (SOM_GetClass) also is available. This method is not typically overridden.


### Related Methods *(hidden)*

somGetClassName


### Example *(hidden)*

```
#include "animal.h"
main()
{
  Animal *myAnimal;
  int numMethods;
  SOMClass *animalClass;

  myAnimal = AnimalNew ();
  animalClass = _somGetClass (myAnimal);
  numMethods = _somGetNumMethods (animalClass);
  somPrintf ("Number of methods supported by Animal: %d\n", numMethods);
  _somFree (myAnimal);
}
/*
Output from this program:
Number of methods supported by Animal: 24
*/
```


### somGetClassData


### Instructions *(hidden)*

Topics: 

Call Syntax 
Uses 
Parameters 
Return Value 
Errors 
Notes 
Related Methods 
Glossary


### Call Syntax *(hidden)*

/* Class:  SOMClass
  *Method :somGetClassData
  *
  *ObtainapointertotheglobalClassData
  *structureassociatedwiththeclass . 
  */
  # include< som . h > 
  SOMClass *receiver;
  somClassDataStructure* cds 
  cds = _somGetClassData (receiver);


### Uses *(hidden)*

This method returns the address of the global ClassData structure associated with the class. Every SOM class has an external data structure named <className>ClassData that holds a pointer to the class object and information about the relative offsets of method table entries. This structure can be used by language bindings to assist in the method resolution process.


### Parameters *(hidden)*

receiver The class object whose ClassData structure is desired.


### Return Value *(hidden)*

Returns a pointer to the ClassData structure for this class.


### Notes *(hidden)*

This method is not generally overridden. It is provided for use by the SOM run-time environment.


### Related Methods *(hidden)*

somSetClassData


### somGetClassMtab


### Instructions *(hidden)*

Topics: 

Call Syntax 
Uses 
Parameters 
Return Value 
Errors 
Notes 
Related Methods 
Example 
Glossary


### Call Syntax *(hidden)*

/* Class:  SOMClass
  *Method :somGetClassMtab
  *
  *Obtainapointertotheclass 'methodtable . 
  */
  # include< som . h > 
  SOMClass *receiver;
  somMethodTab* mtab ; 
  mtab = _somGetClassMtab (receiver);


### Uses *(hidden)*

This method returns the address of the class' method table. The method table is a structure containing a pointer to the class object followed by an array of procedure entry addresses, with one entry for each static method defined in this class or any of its parent classes.


### Parameters *(hidden)*

receiver The class object whose method table is desired.


### Return Value *(hidden)*

Returns a pointer to the method table of this class.


### Notes *(hidden)*

This method is not generally overridden. 

Whenever possible you should avoid writing code that accesses the method table directly, since the specifics of this structure may change in a future release of SOM.


### Related Methods *(hidden)*

somGetNumStaticMethods 
somGetPClsMtab


### Example *(hidden)*

```
#include "animal.h"
void main()
{
   Animal *myAnimal;
   somId somId_setSound;
   somMethodPtr methodPtr;
   somMethodTab *methodTable;
   int offset;
   myAnimal = AnimalNew();
/* ---------------------------------------
   Note: Next five lines are equivalent to
       _setSound(myAnimal, "Roar!!!");
   --------------------------------------- */
   somId_setSound = SOM_IdFromString("setSound");
   methodTable = _somGetClassMtab(_somGetClass(myAnimal));
   offset = _somGetMethodOffset(_somGetClass(myAnimal), somId_setSound);
   methodPtr = methodTable->entries[offset];
   methodPtr(myAnimal, "Roar!!!");
/* --------------------------------------- */
   _display(myAnimal);
   _somFree(myAnimal);
}
/*
Program Output:
This Animal says
Roar!!!
*/
```


### somGetClassName


### Instructions *(hidden)*

Topics: 

Call Syntax 
Uses 
Parameters 
Return Value 
Errors 
Notes 
Related Methods 
Example 
Glossary


### Call Syntax *(hidden)*

/* Class:  SOMObject
  *Method :somGetClassName
  *
  *Obtainthenameoftheclassofanobject . 
  */
  # include< som . h > 
  SOMAny *receiver;
  zStringclassName ; 
  className = _somGetClassName (receiver);


### Uses *(hidden)*

This method returns the address of a zero-terminated string that gives the name of the class of the receiving object.


### Parameters *(hidden)*

receiver The object whose class name is desired.


### Return Value *(hidden)*

Returns a pointer to the name of the class.


### Notes *(hidden)*

This method is not generally overridden. The address returned is valid until the object's class object is unregistered or freed.


### Related Methods *(hidden)*

somGetClass


### Example *(hidden)*

```
#include "animal.h"
main()
{
  Animal *myAnimal;
  SOMClass *animalClass;
  char *className;

  myAnimal = AnimalNew();
  className = _somGetClassName(myAnimal);
  somPrintf("Class name: %s\n", className);
  _somFree(myAnimal);
}
/*
Output from this program:
Class name: Animal
*/
```


### somGetInitFunction


### Instructions *(hidden)*

Topics: 

Call Syntax 
Uses 
Parameters 
Return Value 
Errors 
Notes 
Related Methods 
Glossary


### Call Syntax *(hidden)*

/* Class:  SOMClassMgr
  *Method :somGetInitFunction
  *
  *Obtainthenameofthefunctionthat
  *initializestheSOMclassesinaDLL . 
  */
  # include< som . h > 
  SOMClassMgr *receiver;
  zStringinitFunction ; 
  initFunction = _somGetInitFunction (receiver);


### Uses *(hidden)*

Supplies the name of the initialization function for a DLL containing more than one SOM class.


### Parameters *(hidden)*

receiver Usually SOMClassMgrObject (or an instance of a user-supplied subclass of SOMClassMgr).


### Return Value *(hidden)*

This method returns the zero-terminated string obtained from (*SOMClassInitFuncName)(). By default, this exit is set to return the value, "SOMInitModule".


### Notes *(hidden)*

This method is used by SOMClassMgrObject when it loads a DLL. If the DLL contains an entry point with a matching name, that function is invoked to initialize all of the SOM classes in the DLL.  If the DLL does not contain a matching entry point, an entry-point name of the form <className>NewClass is invoked.  Here <className> is the name of the class known to exist in the DLL. 

Because of this behavior, if you place only a single SOM class in a DLL, its "NewClass" routine (produced by the SOM Compiler) will be invoked automatically to build the class object when the DLL is loaded. If you package more than one SOM class in a single DLL, you must also supply a C-language function named SOMInitModule (or whatever name is ultimately supplied by the somGetInitFunction method) to invoke the class creation routines for all of the classes packaged in the DLL. 

Generally speaking, this is not a method that you would ever invoke yourself. But if you were creating a class derived from SOMClassMgr, you might wish to override this method to define your own convention for functions that initialize class DLLs.


### Related Methods *(hidden)*

somFindClass 
somFindClsInFile


### somGetInstanceOffset


### Instructions *(hidden)*

Topics: 

Call Syntax 
Uses 
Parameters 
Return Value 
Errors 
Notes 
Related Methods 
Example 
Glossary


### Call Syntax *(hidden)*

/* Class:  SOMClass
  *Method :somGetInstanceOffset
  *
  *Obtaintheoffsetofaclass 'instancedata
  *inallofitsobjectinstances . 
  */
  # include< som . h > 
  SOMClass *receiver;
  integer4offset ; 
  offset = _somGetInstanceOffset (receiver);


### Uses *(hidden)*

This method returns the offset in the body portion of all objects of this class where the class' instance data can be found.


### Parameters *(hidden)*

receiver The class object whose instance-data offset is desired.


### Return Value *(hidden)*

Returns the offset (within any object of the receiving class) of the class' instance data. More precisely, this method returns the offset in the body part of instances of this class for the instance data introduced by this class, as the distance in bytes along the class' "left-hand" derivation path. This value is only meaningful For classes in a single-inheritance hierarchy. 

If a class has no instance data, the value 0 is returned. Use somGetInstancePartSize to determine if any instance data actually exists.


### Notes *(hidden)*

This method is not generally overridden. Whenever possible avoid relying on this type of mechanism to access an object's instance data.  Such "back door" access to the internals of an object weakens its ability to encapsulate its implementation, and will not extend in any meaningful way to future class hierarchies which may may use of multiple inheritance. The method is provided for the internal use by the SOM run-time.


### Related Methods *(hidden)*

somGetInstancePartSize 
somGetInstanceSize


### Example *(hidden)*

```
#include "animal.h"
main()
{
  Animal *myAnimal;
  SOMClass *animalClass;
  int instanceSize;
  int instanceOffset;
  int instancePartSize;

  myAnimal = AnimalNew ();
  animalClass = _somGetClass (myAnimal);
  instanceSize = _somGetInstanceSize (animalClass);
  instanceOffset = _somGetInstanceOffset (animalClass);
  instancePartSize = _somGetInstancePartSize (animalClass);
  somPrintf ("Instance Size: %d\n", instanceSize);
  somPrintf ("Instance Offset: %d\n", instanceOffset);
  somPrintf ("Instance Part Size: %d\n", instancePartSize);
  _somFree (myAnimal);
}
/*
Output from this program:
Instance Size: 8
Instance Offset: 0
Instance Part Size: 4
*/
```


### somGetInstancePartSize


### Instructions *(hidden)*

Topics: 

Call Syntax 
Uses 
Parameters 
Return Value 
Errors 
Notes 
Related Methods 
Example 
Glossary


### Call Syntax *(hidden)*

/* Class:  SOMClass
  *Method :somGetInstancePartSize
  *
  *Obtainthesizeofaclass 'instance - data 
  * section in all of its object instances.
  * / 
  #include <som.h>
  SOMClass* receiver ; 
  integer4 size;
  size=_ somGetInstancePartSize( receiver ) ;


### Uses *(hidden)*

This method returns the amount of space needed in an object of this class to contain the class' instance data.


### Parameters *(hidden)*

receiver The class object whose instance-data size is desired.


### Return Value *(hidden)*

Returns the size, in bytes, of the instance data required for this class. This does not include the instance-data space required for this class's ancestor or descendent classes. 

If a class has no instance data, 0 is returned.


### Notes *(hidden)*

This method is not generally overridden.


### Related Methods *(hidden)*

somGetInstanceOffset 
somGetInstanceSize


### Example *(hidden)*

```
#include "animal.h"
main()
{
  Animal *myAnimal;
  SOMClass *animalClass;
  int instanceSize;
  int instanceOffset;
  int instancePartSize;

  myAnimal = AnimalNew ();
  animalClass = _somGetClass (myAnimal);
  instanceSize = _somGetInstanceSize (animalClass);
  instanceOffset = _somGetInstanceOffset (animalClass);
  instancePartSize = _somGetInstancePartSize (animalClass);
  somPrintf ("Instance Size: %d\n", instanceSize);
  somPrintf ("Instance Offset: %d\n", instanceOffset);
  somPrintf ("Instance Part Size: %d\n", instancePartSize);
  _somFree (myAnimal);
}
/*
Output from this program:
Instance Size: 8
Instance Offset: 0
Instance Part Size: 4
*/
```


### somGetInstanceSize


### Instructions *(hidden)*

Topics: 

Call Syntax 
Uses 
Parameters 
Return Value 
Errors 
Notes 
Related Methods 
Example 
Glossary


### Call Syntax *(hidden)*

/* Class:  SOMClass
  *Method :somGetInstanceSize
  *
  *Obtainthesizeofaninstanceof
  *thereceivingclass
  * / 
  #include <som.h>
  SOMClass* receiver ; 
  integer4 size;
  size=_ somGetInstanceSize( receiver ) ;


### Uses *(hidden)*

This method returns the total amount of space needed in an object of this class.


### Parameters *(hidden)*

receiver The class object whose instance size is desired.


### Return Value *(hidden)*

Returns the size, in bytes, of each instance of this class. This includes the instance-data space required for this class and all of its ancestor classes.


### Notes *(hidden)*

This method is not generally overridden.


### Related Methods *(hidden)*

somGetInstanceOffset 
somGetInstancePartSize


### Example *(hidden)*

```
#include "animal.h"
main()
{
  Animal *myAnimal;
  SOMClass *animalClass;
  int instanceSize;
  int instanceOffset;
  int instancePartSize;

  myAnimal = AnimalNew ();
  animalClass = _somGetClass (myAnimal);
  instanceSize = _somGetInstanceSize (animalClass);
  instanceOffset = _somGetInstanceOffset (animalClass);
  instancePartSize = _somGetInstancePartSize (animalClass);
  somPrintf ("Instance Size: %d\n", instanceSize);
  somPrintf ("Instance Offset: %d\n", instanceOffset);
  somPrintf ("Instance Part Size: %d\n", instancePartSize);
  _somFree (myAnimal);
}
/*
Output from this program:
Instance Size: 8
Instance Offset: 0
Instance Part Size: 4
*/
```


### somGetName


### Instructions *(hidden)*

Topics: 

Call Syntax 
Uses 
Parameters 
Return Value 
Errors 
Notes 
Related Methods 
Example 
Glossary


### Call Syntax *(hidden)*

/* Class:  SOMClass
  *Method :somGetName
  *
  *Obtainthenameofaclass . 
  */
  # include< som . h > 
  SOMClass *receiver;
  zStringclassName ; 
  className = _somGetName (receiver);


### Uses *(hidden)*

This method returns the address of a zero-terminated string that gives the name of the receiving class.


### Parameters *(hidden)*

receiver The class whose name is desired.


### Return Value *(hidden)*

Returns a pointer to the name of the class.


### Notes *(hidden)*

This method is not generally overridden. The returned address is valid until the class object is unregistered or freed.


### Related Methods *(hidden)*

somGetClass 
somGetClassName


### Example *(hidden)*

```
#include "animal.h"
main()
{
  Animal *myAnimal;
  SOMClass *animalClass;
  char *className;

  myAnimal = AnimalNew();
  animalClass = _somGetClass(myAnimal);
  className = _somGetName(animalClass);
  somPrintf("Class Name: %s\n", className);
  _somFree(myAnimal);
}
/*
Output from this program:
Class Name: Animal
*/
```


### somGetNumMethods


### Instructions *(hidden)*

Topics: 

Call Syntax 
Uses 
Parameters 
Return Value 
Errors 
Notes 
Related Methods 
Example 
Glossary


### Call Syntax *(hidden)*

/* Class:  SOMClass
  *Method :somGetNumMethods
  *
  *Obtainthenumberofmethods
  *availableforthereceivingclass . 
  */
  # include< som . h > 
  SOMClass *receiver;
  intmethodCount ; 
  methodCount = _somGetNumMethods (receiver);


### Uses *(hidden)*

This method returns the number of methods currently supported by this class, including inherited methods (both static and dynamic).


### Parameters *(hidden)*

receiver The class object whose method count is desired.


### Return Value *(hidden)*

The total number of methods that are currently available for the receiving class.


### Notes *(hidden)*

The value returned by this method is the total number of methods currently registered in the receiving class, including static and dynamic methods, whether defined in this class or inherited from a parent class. Because SOM classes are dynamic, other dynamic methods can be added to the class.  Furthermore, if the class uses dispatch method resolution, all dynamic methods available in this class might not be formally registered.  That is, the dispatch function can permit access to additional methods. 

This method is not generally overridden.


### Related Methods *(hidden)*

somGetNumStaticMethods


### Example *(hidden)*

```
#include "animal.h"
main()
{
  Animal *myAnimal;
  int numMethods;

  myAnimal = AnimalNew();
  numMethods = _somGetNumMethods(_Animal);
  somPrintf("Number of methods supported by class: %d\n", numMethods);
  _somFree(myAnimal);
}
/*
Output from this program:
Number of methods supported by class: 24
*/
```


### somGetNumStaticMethods


### Instructions *(hidden)*

Topics: 

Call Syntax 
Uses 
Parameters 
Return Value 
Errors 
Notes 
Related Methods 
Example 
Glossary


### Call Syntax *(hidden)*

/* Class:  SOMClass
  *Method :somGetNumStaticMethods
  *
  *Obtainthenumberofstaticmethods
  *availableforthereceivingclass . 
  */
  # include< som . h > 
  SOMClass *receiver;
  intmethodCount ; 
  methodCount = _somGetNumStaticMethods (receiver);


### Uses *(hidden)*

This method returns the number of static methods available in this class, including inherited ones.


### Parameters *(hidden)*

receiver The class object whose static method count is desired.


### Return Value *(hidden)*

The total number of static methods that are available for the receiving class.


### Notes *(hidden)*

Static methods are those that can be accessed through the offset resolution mechanism. 

This method is not generally overridden.


### Related Methods *(hidden)*

somGetNumMethods


### Example *(hidden)*

```
#include "animal.h"
main()
{
  Animal *myAnimal;
  SOMClass *animalClass;
  int nStaticMethods;

  myAnimal = AnimalNew();
  animalClass = _somGetClass(myAnimal);
  nStaticMethods = _somGetNumStaticMethods(animalClass);
  somPrintf("Number of static methods: %d\n", nStaticMethods);
  _somFree(myAnimal);
}
/*
Output from this program:
Number of static methods: 24
*/
```


### somGetParent


### Instructions *(hidden)*

Topics: 

Call Syntax 
Uses 
Parameters 
Return Value 
Errors 
Notes 
Related Methods 
Example 
Glossary


### Call Syntax *(hidden)*

/* Class:  SOMClass
  *Method :somGetParent
  *
  *Getapointertotheclass 'parentclass . 
  */
  # include< som . h > 
  SOMClass *receiver;
  SOMClass* parent ; 
  parent = _somGetParent (receiver);


### Uses *(hidden)*

Obtain a pointer to the parent class of the receiver (if a parent exists) and NULL otherwise. If a class has multiple parents, this method returns the parent class along the "left-hand" derivation path.


### Parameters *(hidden)*

receiver The class whose parent class is desired.


### Return Value *(hidden)*

Returns the parent class of the receiver, if one exists, and NULL otherwise.


### Notes *(hidden)*

Because all SOM objects inherit from SOMObject, only the class SOMObject will return NULL.


### Related Methods *(hidden)*

somGetClass


### Example *(hidden)*

```
/* Note: dog is derived from animal. */
#include "dog.h"
main()
{
  Dog *myDog;
  SOMClass *dogClass;
  SOMClass *parentClass;
  char *parentName;

  myDog = DogNew();
  dogClass = _somGetClass(myDog);
  parentClass = _somGetParent(dogClass);
  parentName = _somGetName(parentClass);
  somPrintf("Name of Parent Class: %s\n", parentName);
  _somFree(myDog);
}
/*
Output from this program:
Name of Parent Class: Animal
*/
```


### somGetPClsMtab


### Instructions *(hidden)*

Topics: 

Call Syntax 
Uses 
Parameters 
Return Value 
Errors 
Notes 
Related Methods 
Example 
Glossary


### Call Syntax *(hidden)*

/* Class:  SOMClass
  *Method :somGetPClsMtab
  *
  *Obtainapointertotheparentclass 'methodtable
  * / 
  #include <som.h>
  SOMClass* receiver ; 
  somMethodTab *mtab;
  mtab=_ somGetPClsMtab( receiver ) ;


### Uses *(hidden)*

This method returns the address of the method table for the receiver's parent class.


### Parameters *(hidden)*

receiver The class object whose parent's method table is desired.


### Return Value *(hidden)*

Returns a pointer to the method table of the parent class of the receiving class. If this class is a root class (SOMObject), NULL is returned.


### Notes *(hidden)*

This method is equivalent to: 

```
    _somGetClassMtab (_somGetParent (receiver))
```

This method is not generally overridden. 

Whenever possible you should avoid writing code that accesses the method table directly, since the specifics of this structure may change in a future release of SOM.


### Related Methods *(hidden)*

somGetClassMtab 
somGetNumStaticMethods


### Example *(hidden)*

```
/* --------------------------------
   Note: Dog is derived from Animal
   -------------------------------- */
#include "dog.h"
#include "animal.h"
void main()
{
   Dog *myDog;
   somId somId_setSound;
   somMethodPtr methodPtr;
   somMethodTab *methodTable;
   int offset;
   myDog = DogNew();
/* ---------------------------------------
   Note: Next five lines are equivalent to
       _setSound(myDog, "Woof");
   --------------------------------------- */
   somId_setSound = SOM_IdFromString ("setSound");
   methodTable = _somGetPClsMtab (_somGetClass (myDog));
   offset = _somGetMethodOffset (_somGetParent (_somGetClass(myDog)),
                                 somId_setSound);
   methodPtr = methodTable->entries[offset];
   methodPtr(myDog, "Woof");
/* --------------------------------------- */
   _display(myDog);
   _somFree(myDog);
}
/*
Program Output:
This Animal says
Woof
*/
```


### somGetSize


### Instructions *(hidden)*

Topics: 

Call Syntax 
Uses 
Parameters 
Return Value 
Errors 
Notes 
Related Methods 
Example 
Glossary


### Call Syntax *(hidden)*

/* Class:  SOMObject
  *Method :somGetSize
  *
  *Obtainthesizeofanobject . 
  */
  # include< som . h > 
  SOMAny *receiver;
  integer4size ; 
  size = _somGetSize (receiver);


### Uses *(hidden)*

This method returns the total amount of contiguous space used by the receiving object.


### Parameters *(hidden)*

receiver The object whose size is desired.


### Return Value *(hidden)*

Returns the size in bytes of the receiver.


### Notes *(hidden)*

The value returned reflects only the amount of storage needed to hold the SOM representation of the object.  The object might actually be using or managing additional space outside of this area. 

This method is not generally overridden.


### Related Methods *(hidden)*

somGetInstancePartSize 
somGetInstanceSize


### Example *(hidden)*

```
#include "animal.h"
void main()
{
  Animal *myAnimal;
  int animalSize;
  myAnimal = AnimalNew();
  animalSize = _somGetSize(myAnimal);
  somPrintf("Size of animal (in bytes): %d\n", animalSize);
  _somFree(myAnimal);
}
/*
Output from this program:
Size of animal (in bytes): 8
*/
```


### somInit


### Instructions *(hidden)*

Topics: 

Call Syntax 
Uses 
Parameters 
Return Value 
Errors 
Notes 
Related Methods 
Example 
Glossary


### Call Syntax *(hidden)*

/* Class:  SOMObject
  *Method :somInit
  *
  *Initializesinstancedatainanewlycreatedobject . 
  */
  # include< som . h > 
  SOMAny *receiver;
  _ somInit( receiver ) ;


### Uses *(hidden)*

This method is invoked to cause a newly created object to initialize its instance data.


### Parameters *(hidden)*

receiver The object to be initialized.


### Return Value *(hidden)*

None.


### Notes *(hidden)*

This method initializes instance data in the receiving object. Because instances of SOMObject do not have any instance data, the default implementation does nothing. It is provided to induce consistency among subclasses that require initialization. This method is called automatically as a side effect of object creation by somNew or somRenew. 

A companion method (somUninit) is called whenever an object is freed. These two methods should be designed to work together, with somInit priming an object for its first use, and somUninit preparing the object for subsequent release. 

In general, if objects of your class contain instance-data items, override the somInit method to set your instance data to an appropriate initial state. When overriding this method, always call the parent-class version of this method before doing your own initialization.


### Related Methods *(hidden)*

somNew 
somRenew 
somUninit


### Example *(hidden)*

```
#  animal2.csc:
   include <somobj.sc>
   class: Animal2, local;
   parent: SOMObject;
   data:
     char *sound;
   methods:
      void display();
      override somInit;
      override somUninit;

/* animal2.c: */
   #define Animal2_Class_Source
   #include "animal2.ih"
   #include <string.h>

   SOM_Scope void SOMLINK display (Animal2 *somSelf)
   {
       Animal2Data *somThis = Animal2GetData(somSelf);
   }
   SOM_Scope void SOMLINK somInit (Animal2 *somSelf)
   {
       Animal2Data *somThis = Animal2GetData (somSelf);
       parent_somInit (somSelf);
       _sound = (*SOMMalloc)(100);
       strcpy (_sound, "Unknown Noise");
       somPrintf ("New Animal Initialized\n");
   }
   SOM_Scope void SOMLINK somUninit (Animal2 *somSelf)
   {
       Animal2Data *somThis = Animal2GetData (somSelf);
       (*SOMFree)(_sound);
       somPrintf ("Animal Uninitialized\n");
       parent_somUninit (somSelf);
   }

/* main program */
   #include "animal2.h"
   void main()
   {
      Animal2 *myAnimal;
      myAnimal = Animal2New ();
      _somFree (myAnimal);
   }

/*
Program output:
New Animal Initialized
Animal Uninitialized
*/
```


### somInitClass


### Instructions *(hidden)*

Topics: 

Call Syntax 
Uses 
Parameters 
Return Value 
Errors 
Notes 
Related Methods 
Example 
Glossary


### Call Syntax *(hidden)*

/* Class:  SOMClass
  *Method :somInitClass
  *
  *Initializesanewlycreatedclassobject . 
  */
  # include< som . h > 
  SOMClass *receiver;
  SOMClass* parentClass ; 
  integer4 instanceSize;
  intmaxStaticMethods ; 
  integer4 majorVersion;
  integer4minorVersion ; 
  _somInitClass (receiver, parentClass, instanceSize,
          maxStaticMethods ,majorVersion ,minorVersion ) ;


### Uses *(hidden)*

This method is invoked to complete the construction of a newly created class object.


### Parameters *(hidden)*

receiver The class to be initialized. 

parentClass The class that the newly created class will inherit from. If NULL is specified, this value defaults to SOMObject. Parent classes must be created prior to the creation of any of their descendant classes. 

instanceSize The amount of space needed to hold the instance data defined for the newly created class.  This value should not include any space required by parent class(es). 

maxStaticMethods The number of static methods defined for the new class. It should not include any static methods defined in the parent classes, even if some of them have been overridden in this class. 

majorVersion The major version number associated with the current implementation of the new class. 

minorVersion The minor version number associated with the current implementation of the new class.


### Return Value *(hidden)*

None.


### Notes *(hidden)*

This method is ordinarily invoked from the <Classname>NewClass procedure generated by the SOM Compiler from the OIDL class definition. Overriding this method with one of your own is not recommended. 

Generally speaking, most programmers would never make any direct use of this method. It is provided for use by the C-language bindings produced by the SOM Compiler.


### Related Methods *(hidden)*

somClassReady 
somRegisterClass


### Example *(hidden)*

```
   #include <som.h>
   SOMClass *myParentClass;
   struct {
      int a, b, c;
   } myClassInstanceData;
   #define MyClass_MaxMethods 4
   #define MyClass_MajorVersion 2
   #define MyClass_MinorVersion 1
   extern struct MyClassClassDataStructure {
        SOMAny *classObject;
        somMOffset myMethod1;
        somMOffset myMethod2;
        somMOffset myMethod3;
        somMOffset myMethod4;
   } MyClassClassData;

   /* ... */
   _somInitClass (MyClassClassData.classObject,
               "Animal",
               myParentClass,
               sizeof (myClassInstanceData),
               MyClass_MaxMethods,
               MyClass_MajorVersion,
               MyClass_MinorVersion);
```


### somIsA


### Instructions *(hidden)*

Topics: 

Call Syntax 
Uses 
Parameters 
Return Value 
Errors 
Notes 
Related Methods 
Example 
Glossary


### Call Syntax *(hidden)*

/* Class:  SOMObject
  *Method :somIsA
  *
  *Determineifanobjectisaninstanceofagiven
  *class( orofoneofitsdescendantclasses ) . 
  */
  # include< som . h > 
  SOMAny *receiver;
  SOMClass* aClass ; 
  int result;
  result=_ somIsA( receiver ,aClass ) ;


### Uses *(hidden)*

Use this method to determine if an object can be treated like an instance of aClass.


### Parameters *(hidden)*

receiver The object to be tested. 

aClass The class that the object should be tested against.


### Return Value *(hidden)*

Returns 1 (true) if the receiving object is an instance of the specified class or of any of its descendant classes, and 0 (false) if otherwise.


### Notes *(hidden)*

A class object is considered to be descended from itself for the purposes of this method. 

Because classes are frequently used as a static typing mechanism, this test is really a way of ascertaining if an object is of a particular static type.


### Related Methods *(hidden)*

somIsDescendedFrom 
somIsInstanceOf


### Example *(hidden)*

```
#include "animal.h"
#include "dog.h"
/* --------------------------------
   Note: Dog is derived from Animal.
   -------------------------------- */
main()
{
  Animal *myAnimal;
  Dog *myDog;
  SOMClass *animalClass;
  SOMClass *dogClass;

  myAnimal = AnimalNew();
  myDog = DogNew();
  animalClass = _somGetClass (myAnimal);
  dogClass = _somGetClass (myDog);
  if (_somIsA (myDog, animalClass))
     somPrintf ("myDog IS an Animal\n");
  else
     somPrintf ("myDog IS NOT an Animal\n");
  if (_somIsA (myAnimal, dogClass))
     somPrintf ("myAnimal IS a Dog\n");
  else
     somPrintf ("myAnimal IS NOT a Dog\n");
  _somFree (myAnimal);
}
/*
Output from this program:
myDog IS an Animal
myAnimal IS NOT a Dog
*/
```


### somIsInstanceOf


### Instructions *(hidden)*

Topics: 

Call Syntax 
Uses 
Parameters 
Return Value 
Errors 
Notes 
Related Methods 
Example 
Glossary


### Call Syntax *(hidden)*

/* Class:  SOMObject
  *Method :somIsInstanceOf
  *
  *Determineifanobjectisaninstanceofa
  *specificclass . 
  */
  # include< som . h > 
  SOMAny *receiver;
  SOMClass* aClass ; 
  int result;
  result=_ somIsInstanceOf( receiver ,aClass ) ;


### Uses *(hidden)*

Use this method to determine if an object is an instance of a specific class.


### Parameters *(hidden)*

receiver The object to be tested. 

aClass The class that the object should be an instance of.


### Return Value *(hidden)*

Returns 1 (true) if the receiving object is an instance of the specified class, and 0 (false) if otherwise.


### Notes *(hidden)*

This method tests an object for inclusion in one specific class. It is equivalent to the expression: 

```
    (aClass == somGetClass (receiver))
```


### Related Methods *(hidden)*

somIsDescendedFrom 
somIsA


### Example *(hidden)*

```
#include "animal.h"
#include "dog.h"
/* --------------------------------
   Note: Dog is derived from Animal.
   -------------------------------- */
main()
{
  Animal *myAnimal;
  Dog *myDog;
  SOMClass *animalClass;
  SOMClass *dogClass;

  myAnimal = AnimalNew ();
  myDog = DogNew ();
  animalClass = _somGetClass (myAnimal);
  dogClass = _somGetClass (myDog);
  if (_somIsInstanceOf (myDog, animalClass))
     somPrintf ("myDog is an instance of Animal\n");
  if (_somIsInstanceOf (myDog, dogClass))
     somPrintf ("myDog is an instance of Dog\n");
  if (_somIsInstanceOf (myAnimal, animalClass))
     somPrintf ("myAnimal is an instance of Animal\n");
  if (_somIsInstanceOf (myAnimal, dogClass))
     somPrintf ("myAnimal is an instance of Dog\n");
  _somFree (myAnimal);
  _somFree (myDog);
}
/*
Output from this program:
myDog is an instance of Dog
myAnimal is an instance of Animal
*/
```


### somLoadClassFile


### Instructions *(hidden)*

Topics: 

Call Syntax 
Uses 
Parameters 
Return Value 
Errors 
Notes 
Related Methods 
Glossary


### Call Syntax *(hidden)*

/* Class:  SOMClassMgr
  *Method :somLoadClassFile
  *
  *Dynamicallyloadaclass . 
  */
  # include< som . h > 
  SOMClassMgr *receiver;
  somIdclassId ; 
  int majorVersion;
  intminorVersion ; 
  zString file;
  SOMClass* class ; 
  class = _somLoadClassFile (receiver, classId, majorVersion,
               minorVersion ,file ) ;


### Uses *(hidden)*

The SOMClassMgr object uses this method to load a class dynamically during the processing of somFindClass or somFindClsInFile. A SOM class object representing the class is expected to be created and registered as a result of this action.


### Parameters *(hidden)*

receiver Usually SOMClassMgrObject (or an instance of a user-supplied subclass of SOMClassMgr). 

classId The ID representing the name of the class to load. 

majorVersion The major version number used to check the compatibility of the class' implementation with the caller's expectations. 

minorVersion The minor version number used to check the compatibility of the class' implementation with the caller's expectations. 

file The name of the DLL file containing the class. The name can be either a simple, unqualified name, without any extension (in which case the OS/2* LIBPATH is searched for a file with the extension, .DLL) or a fully-qualified file name (in which case the OS/2* LIBPATH is not searched).


### Return Value *(hidden)*

Returns a pointer to the class object, or NULL if the class could not be loaded, or the class object could not be created.


### Notes *(hidden)*

You can override this method to load or create classes dynamically using your own mechanisms, rather than using the DLL approach supplied with SOM. If you simply wish to change the name of the DLL procedure that is called to initialize the classes in the DLL, override somGetInitFunction instead. 

Generally speaking, you will probably never need to make any direct use of this method. Use somFindClass or somFindClsInFile instead.


### Related Methods *(hidden)*

somFindClass 
somFindClsInFile 
somGetInitFunction 
somUnloadClassFile


### somLocateClassFile


### Instructions *(hidden)*

Topics: 

Call Syntax 
Uses 
Parameters 
Return Value 
Errors 
Notes 
Related Methods 
Glossary


### Call Syntax *(hidden)*

/* Class:  SOMClassMgr
  *Method :somLocateClassFile
  *
  *Determinethefilethatholdsa
  *classtobedynamicallyloaded . 
  */
  # include< som . h > 
  SOMClassMgr *receiver;
  somIdclassId ; 
  int majorVersion;
  intminorVersion ; 
  zString file;
  file=_ somLocateClassFile( receiver ,classId ,majorVersion , 
                minorVersion);


### Uses *(hidden)*

The SOMClassMgr object uses this method during somFindclass processing to obtain the name of a file to use when dynamically loading a class.


### Parameters *(hidden)*

receiver Usually SOMClassMgrObject (or an instance of a user-supplied subclass of SOMClassMgr). 

classId The ID representing the name of the class to locate. 

majorVersion The major version number used to check the compatibility of the class' implementation with the caller's expectations. 

minorVersion The minor version number used to check the compatibility of the class' implementation with the caller's expectations.


### Return Value *(hidden)*

Returns the name of the DLL file containing the class. The default implementation in SOMClassMgr simply returns the name of the class.


### Notes *(hidden)*

If you override this method in a user-supplied subclass the name you return can be either a simple, unqualified name without any extension (in which case the OS/2* LIBPATH is searched for a file with the extension, .DLL) or a fully-qualified file name (in which case the OS/2* LIBPATH is not searched). 

Generally speaking, you would not invoke this method directly. It is provided to permit customization of SOMClassMgr through subclassing.


### Related Methods *(hidden)*

somFindClass 
somFindClsInFile 
somGetInitFunction 
somLoadClassFile 
somUnloadClassFile


### somMergeInto


### Instructions *(hidden)*

Topics: 

Call Syntax 
Uses 
Parameters 
Return Value 
Errors 
Notes 
Related Methods 
Example 
Glossary


### Call Syntax *(hidden)*

/* Class:  SOMClassMgr
  *Method :somMergeInto
  *
  *TransfersSOMclassregistryto
  *anotherSOMClassMgrinstance . 
  */
  # include< som . h > 
  SOMClassMgr *receiver;
  SOMClassMgr* target ; 
  _somMergeInto (receiver, target);


### Uses *(hidden)*

This method transfers the SOMClassMgr registry information from the receiver to the target. The target object is required to be an instance of SOMClassMgr or one of its subclasses. At the completion of this operation, the target object can function as a replacement for the receiver; the receiver object (which is then in a newly uninitialized state) is freed. If the receiving object is the distinguished instance pointed to from the global variable, SOMClassMgrObject, SOMCLassMgrObject is then reassigned to point to the target object.


### Parameters *(hidden)*

receiver Usually SOMClassMgrObject (or an instance of a user-supplied subclass of SOMClassMgr). 

target Another instance of SOMClassMgr or one of its subclasses.


### Return Value *(hidden)*

None.


### Notes *(hidden)*

Subclasses that override this method should also transfer their section of the object, then pass this method to their parent as the final step. 

Use this method only if you are creating your own special-purpose SOMClassMgr with a derived class. Invoke somMergeInto from your override of the SOMClassMgr somNew method.


### Related Methods *(hidden)*

None.


### Example *(hidden)*

```
   /*
    * The following example is a hypothetical
    * implementation of an override of the somNew method
    * in a subclass of SOMClassMgr.  It illustrates the
    * proper use of the somMergeInto method.
    */
   SOM_Scope SOMAny * SOMLINK somNew (MySOMClassMgr *somSelf)
   {
       SOMAny *newInstance;
       static int firstTime = 1;
       /*
        * Permit only one instance of MySOMClassMgr to be created.
        */
       if (!firstTime)
          return (SOMClassMgrObject);
       newInstance = parent_somNew (somSelf);
       /*
        * The next line will transfer the class registry
        * information from SOMClassMgrObject into our
        * new instance.
        */
       _somMergeInto (SOMClassMgrObject, newInstance);
       /* As a result of the above operation
        * SOMClassMgrObject is now set to point to the
        * new instance of MySOMClassMgr.
        */
       firstTime = 0;
       return (newInstance);
   }
```


### somNew


### Instructions *(hidden)*

Topics: 

Call Syntax 
Uses 
Parameters 
Return Value 
Errors 
Notes 
Related Methods 
Example 
Glossary


### Call Syntax *(hidden)*

/* Class:  SOMClass
  *Method :somNew
  *
  *Createanewobjectinstance . 
  */
  # include< som . h > 
  SOMClass *receiver;
  SOMAny* newObject ; 
  newObject = _somNew (receiver);


### Uses *(hidden)*

This method creates a new initialized instance of the receiving class.


### Parameters *(hidden)*

receiver The class object that is to create a new instance.


### Return Value *(hidden)*

A pointer to the newly created object.


### Notes *(hidden)*

When this method is applied to the class, SOMClass, or to any other metaclass object, it produces a new class object; when applied to a regular class object, it produces an instance of that class. 

If the allocation of a new object instance fails, an error condition is raised, and the (*SOMError)() routine is called. 

The somInit method is automatically invoked on the newly created object to allow it in properly initialize itself. 

The C-language bindings produced by the SOM Compiler contain a macro of the form ClassnameNew (in the .H file for each class). This is a convenient shorthand for _somNew(_<Classname>).


### Related Methods *(hidden)*

somInit 
somNewNoInit 
somRenew 
somRenewNoInit


### Example *(hidden)*

```
#include "animal.h"
void main(int argc)
{
   Animal *myAnimal;
/* -------------------------------------------------
   Note: next 2 lines are functionally equivalent to
       myAnimal = AnimalNew();
   ------------------------------------------------- */
   AnimalNewClass(0,0);
   myAnimal = _somNew(_Animal);
   /* ... */
   _somFree(myAnimal);
}
```


### somNewNoInit


### Instructions *(hidden)*

Topics: 

Call Syntax 
Uses 
Parameters 
Return Value 
Errors 
Notes 
Related Methods 
Example 
Glossary


### Call Syntax *(hidden)*

/* Class:  SOMClass
  *Method :somNewNoInit
  *
  *Createanewobjectinstance . 
  */
  # include< som . h > 
  SOMClass *receiver;
  SOMAny* newObject ; 
  newObject = _somNewNoInit (receiver);


### Uses *(hidden)*

This method creates a new instance of the receiving class, without invoking the somInit method to perform object initialization.


### Parameters *(hidden)*

receiver The class object that is to create a new instance.


### Return Value *(hidden)*

A pointer to the newly created object.


### Notes *(hidden)*

This method is identical to somNew, except that the somInit method is not invoked on the newly created object. If you are writing your own class methods or constructors, using somNewNoInit permits you to separate the actions involved in object creation and initialization to suit your own needs.


### Related Methods *(hidden)*

somNew 
somRenew 
somRenewNoInit


### Example *(hidden)*

```
#include "animal.h"
void main(int argc)
{
   Animal *myAnimal;
/* -------------------------------------------------
   Note: next 3 lines are functionally equivalent to
       myAnimal = AnimalNew();
   ------------------------------------------------- */
   AnimalNewClass(0,0);
   myAnimal = _somNewNoInit(_Animal);
   _somInit(myAnimal);
   /* ... */
   _somFree(myAnimal);
}
```


### somOverrideSMethod


### Instructions *(hidden)*

Topics: 

Call Syntax 
Uses 
Parameters 
Return Value 
Errors 
Notes 
Related Methods 
Example 
Glossary


### Call Syntax *(hidden)*

/* Class:  SOMClass
  *Method :somOverrideSMethod
  *
  *Addamethodtoaclassthat
  *overridesaparentmethod . 
  */
  # include< som . h > 
  SOMClass *receiver;
  somIdmethodId ; 
  somMethodProc *method;
  _ somOverrideSMethod( receiver ,methodId ,method ) ;


### Uses *(hidden)*

This method can be used instead of somAddStaticMethod when it is known that the class' parent class already supports this method. This method does not require the method descriptor and stub methods that the others do.


### Parameters *(hidden)*

receiver The class to which the method should be added. 

methodId An ID specifying the name of the method to override. 

method The procedure entry address for the method.


### Return Value *(hidden)*

None.


### Notes *(hidden)*

This method is ordinarily invoked from the <Classname>NewClass procedure generated by the SOM Compiler from the OIDL class definition. Overriding this method with one of your own is not recommended. 

Generally speaking, you would never use this method directly. It is provided for the use of the C-language binding code produced by the SOM Compiler.


### Related Methods *(hidden)*

somAddStaticMethod 
somInitClass


### Example *(hidden)*

You will find examples of this method in code generated by the SOM Compiler if you look in the .IH file of any class with overriding methods.


### somPrintSelf


### Instructions *(hidden)*

Topics: 

Call Syntax 
Uses 
Parameters 
Return Value 
Errors 
Notes 
Related Methods 
Example 
Glossary


### Call Syntax *(hidden)*

/* Class:  SOMObject
  *Method :somPrintSelf
  *
  *Writesadetaileddescriptionofthereceiving
  *objectto( * SOMOutCharRoutine ) ( char ) ; 
  */
  # include< som . h > 
  SOMAny *receiver;
  SOMAny* rcvrSelf ; 
  rcvrSelf = _somPrintSelf (receiver);


### Uses *(hidden)*

This method uses SOMOutCharRoutine to write a brief string with identifying information about the receiving object. The default implementation gives only the object's class name and its address in memory.


### Parameters *(hidden)*

receiver The object to be "printed."


### Return Value *(hidden)*

The receiving object returns a pointer to itself.


### Notes *(hidden)*

None.


### Related Methods *(hidden)*

somDumpSelf 
somDumpSelfInt


### Example *(hidden)*

```
#include "animal.h"
main()
{
  Animal *myAnimal;
  myAnimal = AnimalNew ();
  /* ... */
  _somPrintSelf (myAnimal);
  _somFree (myAnimal);
}
/*
Output from this program:
{An instance of class Animal at address 0001CEC0}
*/
```


### somRegisterClass


### Instructions *(hidden)*

Topics: 

Call Syntax 
Uses 
Parameters 
Return Value 
Errors 
Notes 
Related Methods 
Glossary


### Call Syntax *(hidden)*

/* Class:  SOMClassMgr
  *Method :somRegisterClass
  *
  *Addaclassobjecttothe
  *SOMrun - timeclassregistry . 
  */
  # include< som . h > 
  SOMClassMgr *receiver;
  SOMClass* classObj ; 
  _somRegisterClass (receiver, classObj);


### Uses *(hidden)*

This method adds a class object to the SOM run-time class registry maintained by SOMClassMgrObject.


### Parameters *(hidden)*

receiver Usually SOMClassMgrObject (or an instance of a user-supplied subclass of SOMClassMgr). 

classObj The class object to add to the SOM class registry.


### Return Value *(hidden)*

None.


### Notes *(hidden)*

All SOM run-time class objects should be registered with SOMClassMgrObject. In the C-language bindings created by the SOM Compiler, this is done automatically within the <Classname>NewClass procedure generated for each class (during the execution of the somClassReady method). 

You never need to invoke this method directly.


### Related Methods *(hidden)*

somUnregisterClass


### somRenew


### Instructions *(hidden)*

Topics: 

Call Syntax 
Uses 
Parameters 
Return Value 
Errors 
Notes 
Related Methods 
Example 
Glossary


### Call Syntax *(hidden)*

/* Class:  SOMClass
  *Method :somRenew
  *
  *Createanewobjectinstance
  *usingapassedblockofstorage . 
  */
  # include< som . h > 
  SOMClass *receiver;
  void* storageForObject 
  SOMAny *newObject;
  newObject=_ somRenew( receiver ,storageForObject ) ;


### Uses *(hidden)*

This method creates a new instance of the receiving class, but uses the space pointed to by newObject rather than allocating new space for the object. The default implementation of somRenew automatically re-initializes the object by invoking its somInit method.


### Parameters *(hidden)*

receiver The class object that is to create a new instance. 

storageForObject A pointer to the space to be used to construct a new object.


### Return Value *(hidden)*

The pointer supplied by the caller is returned, but is now a pointer to a valid, initialized object.


### Notes *(hidden)*

No check is made to ensure that the passed pointer addresses enough space to hold an instance of the receiving class. The caller can determine the amount of space necessary by using somGetInstanceSize. 

The C-language bindings produced by the SOM Compiler contain a macro of the form <Classname>Renew (in the .H file for each class). This is a convenient shorthand for _somRenew(_<Classname>).


### Related Methods *(hidden)*

somGetInstanceSize 
somInit 
somNew 
somNewNoInit 
somRenewNoInit


### Example *(hidden)*

```
#include "animal.h"
#include <som.h>
#include <stdlib.h>
main()
{
  char *myAnimalCluster;
  Animal *animals[5];
  SOMClass *animalClass;
  int animalSize, i;

  animalClass = AnimalNewClass();
  animalSize = _somGetInstanceSize (animalClass);
  /* Round up to doubleword multiple */
  animalSize = ((animalSize+3)/4)*4;
  /*
   * Next line allocates room for 5 objects
   * in a "cluster" with a single memory-
   * allocation operation.
   */
  myAnimalCluster = (char *) malloc (5*animalSize);
  /*
   * The for-loop that follows creates 5 initialized
   * Animal instances within the memory cluster.
   */
  for (i=0; i<5; i++)
     animals[i] = _somRenew (animalClass, (void *)(myAnimalCluster+(i*animalSize)));
  /*
   * Finally, the next line frees all 5 animals
   * with one operation.
   */
  free ((void *)myAnimalCluster);
}
```


### somRenewNoInit


### Instructions *(hidden)*

Topics: 

Call Syntax 
Uses 
Parameters 
Return Value 
Errors 
Notes 
Related Methods 
Example 
Glossary


### Call Syntax *(hidden)*

/* Class:  SOMClass
  *Method :somRenewNoInit
  *
  *Createanewobjectinstance
  *usingapassedblockofstorage . 
  */
  # include< som . h > 
  SOMClass *receiver;
  void* storageForObject ; 
  SOMAny *newObject;
  newObject=_ somRenewNoInit( receiver ,storageForObject ) ;


### Uses *(hidden)*

This method creates a new instance of the receiving class, but uses the space pointed to by newObject rather than allocating new space for the object.


### Parameters *(hidden)*

receiver The class object that is to create a new instance. 

storageForObject A pointer to the space to be used to construct a new object.


### Return Value *(hidden)*

The pointer supplied by the caller is returned, but is now a pointer to a valid, but un-initialized, object.


### Notes *(hidden)*

The default implementation of somRenewNoInit differs from somRenew only in that it does not invoke the somInit method to automatically re-initialize the new object.


### Related Methods *(hidden)*

somGetInstanceSize 
somInit 
somNew 
somNewNoInit 
somRenew


### Example *(hidden)*

```
#include "animal.h"
#include <som.h>
#include <stdlib.h>
main()
{
  char *myAnimalCluster;
  Animal *animals[5];
  SOMClass *animalClass;
  int animalSize, i;

  animalClass = AnimalNewClass();
  animalSize = _somGetInstanceSize (animalClass);
  /* Round up to doubleword multiple */
  animalSize = ((animalSize+3)/4)*4;
  /*
   * Next line allocates room for 5 objects
   * in a "cluster" with a single memory-
   * allocation operation.
   */
  myAnimalCluster = (char *) malloc (5*animalSize);
  /*
   * The for-loop that follows creates 5 un-initialized
   * Animal instances within the memory cluster.
   */
  for (i=0; i<5; i++) {
     animals[i] = _somRenewNoInit (animalClass, (void *)(myAnimalCluster+(i*animalSize)));
  }
  /*
   * Finally, the next line frees all 5 animals
   * with one operation.
   */
  free ((void *)myAnimalCluster);
}
```


### somRespondsTo


### Instructions *(hidden)*

Topics: 

Call Syntax 
Uses 
Parameters 
Return Value 
Errors 
Notes 
Related Methods 
Example 
Glossary


### Call Syntax *(hidden)*

/* Class:  SOMObject
  *Method :somRespondsTo
  *
  *Indicateswhetheranobject
  *supportsagivenmethod . 
  */
  # include< som . h > 
  SOMAny *receiver;
  somIdmethodId ; 
  int result;
  result=_ somRespondsTo( receiver ,methodId ) ;


### Uses *(hidden)*

Use this method to determine if an object supports a specified method.


### Parameters *(hidden)*

receiver The object to be tested. 

methodId An ID that represents the name of the desired method.


### Return Value *(hidden)*

Returns 1 (true) if the receiving object supports the specified method, and 0 (false) if otherwise.


### Notes *(hidden)*

Dynamic typing mechanisms are sometimes based on protocol rather than inheritance. That is, an object is considered to be of the correct type if it can respond to an appropriate set of methods, regardless of its class or the parentage of its class. This method can be used as a basis for a dynamic typing system.


### Related Methods *(hidden)*

somSupportsMethod


### Example *(hidden)*

```
/* -----------------------------------------------
   Note: Animal supports a setSound method;
         Animal does not support a doTrick method.
   ----------------------------------------------- */
#include "animal.h"
main()
{
  Animal *myAnimal;
  char *methodName1 = "setSound";
  char *methodName2 = "doTrick";

  myAnimal = AnimalNew();
  if (_somRespondsTo(myAnimal, SOM_IdFromString(methodName1)))
     somPrintf("myAnimal responds to %s\n", methodName1);
  if (_somRespondsTo(myAnimal, SOM_IdFromString(methodName2)))
     somPrintf("myAnimal responds to %s\n", methodName2);
  _somFree(myAnimal);
}
/*
Output from this program:
myAnimal responds to setSound
*/
```


### somSetClassData


### Instructions *(hidden)*

Topics: 

Call Syntax 
Uses 
Parameters 
Return Value 
Errors 
Notes 
Related Methods 
Glossary


### Call Syntax *(hidden)*

/* Class:  SOMClass
  *Method :somSetClassData
  *
  *Setstheclass 'pointertoitsglobal
  *ClassDatastructure . 
  */
  # include< som . h > 
  SOMClass *receiver;
  somClassDataStructureXyzClassData ; 
  _somSetClassData (receiver, &XyzClassData);


### Uses *(hidden)*

This method sets the class' pointer to its global ClassData structure. Every SOM class has an external data structure named <className>ClassData that holds a pointer to the class object and information about the relative offsets of method table entries.


### Parameters *(hidden)*

receiver The class object whose ClassData structure pointer is to be set.


### Return Value *(hidden)*

None.


### Notes *(hidden)*

This method is not generally overridden. It is provided for use by the SOM run-time environment.


### Related Methods *(hidden)*

somGetClassData


### somSupportsMethod


### Instructions *(hidden)*

Topics: 

Call Syntax 
Uses 
Parameters 
Return Value 
Errors 
Related Methods 
Example 
Glossary


### Call Syntax *(hidden)*

/* Class:  SOMClass
  *Method :somSupportsMethod
  *
  *Indicateswhetherinstancesofthis
  *classsupportagivenmethod . 
  */
  # include< som . h > 
  SOMClass *receiver;
  somIdmethodId ; 
  int result;
  result=_ somSupportsMethod( receiver ,methodId ) ;


### Uses *(hidden)*

Use this method to determine if instances of the receiving class support a specified method.


### Parameters *(hidden)*

receiver The class object to be tested. 

methodId An ID that represents the name of the desired method.


### Return Value *(hidden)*

Returns 1 (true) if instances of the receiving class object support the specified method, and 0 (false) if otherwise.


### Related Methods *(hidden)*

somRespondsTo


### Example *(hidden)*

```
/* -----------------------------------------------
   Note: animal supports a setSound method;
         animal does not support a doTrick method.
   ----------------------------------------------- */
#include "animal.h"
main()
{
  Animal *myAnimal;
  SOMClass *animalClass;
  char *methodName1 = "setSound";
  char *methodName2 = "doTrick";

  myAnimal = AnimalNew();
  animalClass = _somGetClass(myAnimal);
  if (_somSupportsMethod(animalClass, SOM_IdFromString(methodName1)))
     somPrintf("Animals respond to %s\n", methodName1);
  if (_somSupportsMethod(animalClass, SOM_IdFromString(methodName2)))
     somPrintf("Animals respond to %s\n", methodName2);
  _somFree(myAnimal);
}
/*
Output from this program:
Animals respond to setSound
*/
```


### somUninit


### Instructions *(hidden)*

Topics: 

Call Syntax 
Uses 
Parameters 
Return Value 
Errors 
Notes 
Related Methods 
Example 
Glossary


### Call Syntax *(hidden)*

/* Class:  SOMObject
  *Method :somUninit
  *
  *Un - initializesthereceivingobject . 
  */
  # include< som . h > 
  SOMAny *receiver;
  _ somUninit( receiver ) ;


### Uses *(hidden)*

This method performs the inverse of object initialization on the receiving object.  It must release any resources acquired by the object during its somInit processing.


### Parameters *(hidden)*

receiver The object to be un-initialized.


### Return Value *(hidden)*

None.


### Notes *(hidden)*

Use this method to clean up anything necessary, such as dynamically allocated storage. However this method does not release the actual storage assigned to the object instance. This method is provided as a complement to somFree, which also releases the storage associated with a dynamically allocated object. Usually you would invoke only somFree (which always calls somUninit). However, in cases where somRenew was used to create an object instance, somFree cannot be called, and you must call somUninit explicitly. 

When overriding this method, always call the parent-class version of this method after doing your own un-initialization.


### Related Methods *(hidden)*

somInit 
somNew 
somRenew


### Example *(hidden)*

```
#  animal2.csc:
   include <somobj.sc>
   class: Animal2, local;
   parent: SOMObject;
   data:
     char *sound;
   methods:
      void display();
      override somInit;
      override somUninit;

/* animal2.c: */
   #define Animal2_Class_Source
   #include "animal2.ih"
   #include <string.h>

   SOM_Scope void SOMLINK display (Animal2 *somSelf)
   {
       Animal2Data *somThis = Animal2GetData(somSelf);
   }
   SOM_Scope void SOMLINK somInit (Animal2 *somSelf)
   {
       Animal2Data *somThis = Animal2GetData (somSelf);
       parent_somInit (somSelf);
       _sound = (*SOMMalloc)(100);
       strcpy (_sound, "Unknown Noise");
       somPrintf ("New Animal Initialized\n");
   }
   SOM_Scope void SOMLINK somUninit (Animal2 *somSelf)
   {
       Animal2Data *somThis = Animal2GetData (somSelf);
       (*SOMFree)(_sound);
       somPrintf ("Animal Uninitialized\n");
       parent_somUninit (somSelf);
   }

/* main program */
   #include "animal2.h"
   void main()
   {
      Animal2 *myAnimal;
      myAnimal = Animal2New ();
      _somFree (myAnimal);
   }

/*
Program output:
New Animal Initialized
Animal Uninitialized
*/
```


### somUnloadClassFile


### Instructions *(hidden)*

Topics: 

Call Syntax 
Uses 
Parameters 
Return Value 
Errors 
Notes 
Related Methods 
Glossary


### Call Syntax *(hidden)*

/* Class:  SOMClassMgr
  *Method :somUnloadClassFile
  *
  *Unloadsadynamicallyloaded
  *classandfreestheclassobject . 
  */
  # include< som . h > 
  SOMClassMgr *receiver;
  SOMClass* class ; 
  int errorCode;
  errorCode=_ somUnloadClassFile( receiver ,class ) ;


### Uses *(hidden)*

The SOMClassMgr object uses this method to unload a dynamically loaded class during somUnregisterClass processing.


### Parameters *(hidden)*

receiver Usually SOMClassMgrObject (or an instance of a user-supplied subclass of SOMClassMgr). 

class The class to unload.


### Return Value *(hidden)*

Returns 0 if the class was successfully unloaded, or a system-specific non-zero error code from DosFreeModule.


### Notes *(hidden)*

The class object is freed whether or not the class' DLL could be unloaded. If the class was not registered, an error condition is raised and (*SOMError)() is invoked. This method is provided to permit user-created subclasses of SOMClassMgr to handle the unloading of classes. 

Do not invoke this method directly; invoke somUnregisterClass instead.


### Related Methods *(hidden)*

somLoadClassFile 
somRegisterClass 
somUnregisterClass


### somUnregisterClass


### Instructions *(hidden)*

Topics: 

Call Syntax 
Uses 
Parameters 
Return Value 
Errors 
Notes 
Related Methods 
Example 
Glossary


### Call Syntax *(hidden)*

/* Class:  SOMClassMgr
  *Method :somUnregisterClass
  *
  *Removesaclassobjectfrom
  *theSOMrun - timeclassregistry . 
  */
  # include< som . h > 
  SOMClassMgr *receiver;
  SOMClass* class ; 
  int errorCode;
  errorCode=_ somUnregisterClass( receiver ,class ) ;


### Uses *(hidden)*

This method unregisters a SOM class, unloads its DLL (if it was dynamically loaded), and frees the class object.


### Parameters *(hidden)*

receiver Usually SOMClassMgrObject (or an instance of a user-supplied subclass of SOMClassMgr). 

class The class to unregister.


### Return Value *(hidden)*

This method returns 0 for a successful completion, or non-zero for a failure.


### Notes *(hidden)*

This method uses somUnloadClassfile to delete a dynamically loaded class.


### Related Methods *(hidden)*

somLoadClassFile 
somRegisterClass 
somUnloadClassFile


### Example *(hidden)*

```
   #include <som.h>

   int rc;
   /*
    * Assume variable "class" points to
    * a class object to be unregistered
    */
   SOMClass *class;

   rc = _somUnregisterClass (SOMClassMgrObject, class);
   if (rc)
      somPrintf ("Could not unregister %s, error code was: %d.\n,
         _somGetName (class), rc);
```


## Appendix A: Error Codes

Value Symbolic Name and Description 

20011 SOMERROR_CCNullClass 
Explanation: The somDescendedFrom method was passed a null class argument. 

20029 SOMERROR_SompntOverflow 
Explanation: The internal buffer used in somPrintf overflowed. 

20039 SOMERROR_MethodNotFound 
Explanation: somFindMethodOk failed to find the indicated method. 

20049 SOMERROR_StaticMethodTableOverflow 
Explanation: A Method-table overflow occurred in somAddStaticMethod. 

20059 SOMERROR_DefaultMethod 
Explanation: The somDefaultMethod was called; a defined method probably was not added before it was invoked. 

20069 SOMERROR_MissingMethod 
Explanation: The specified method was not defined on the target object. 

20079 SOMERROR_BadVersion 
Explanation: An attempt to load, create, or use a version of a class-object implementation is incompatible with the using program. 

20089 SOMERROR_NullId 
SOM_CheckId was given a null ID to check 

20099 SOMERROR_OutOfMemory 
Explanation: Memory is exhausted. 

20109 SOMERROR_TestObjectFailure 
Explanation: somObjectTest found problems with the object it was testing. 

20119 SOMERROR_FailedTest 
Explanation: somTest detected a failure; generated only by test code. 

20121 SOMERROR_ClassNotFound 
Explanation: somFindClass could not find the requested class. 

20131 SOMERROR_OldMethod 
Explanation: An old-style method name was used; change to an appropriate name. 

20149 SOMERROR_CouldNotStartup 
Explanation: somEnvironmentNew failed to complete. 

20159 SOMERROR_NotRegistered 
Explanation: somUnloadClassFile argument was not a registered class. 

20169 SOMERROR_BadOverride 
Explanation: somOverrideSMethod was invoked for a method that was not defined in a parent class. 

20179 SOMERROR_NotImplementedYet 
Explanation: The method raising the error message is not implemented yet. 

20189 SOMERROR_MustOverride 
Explanation: The method raising the error message should have been overridden. 

20199 SOMERROR_BadArgument 
Explanation: An argument to a core SOM method failed a validity test. 

20219 SOMERROR_NoParentClass 
Explanation: During the creation of a class object, the parent class could not be found. 

20229 SOMERROR_NoMetaClass 
Explanation: During the creation of a class object, the metaclass object could not be found.


## Glossary

class A way of categorizing objects based on their behavior and shape.  A class is, in effect, a definition of a generic object. In SOM, a class is a special kind of object that can manufacture other objects that all have a common shape and exhibit similar behavior (more precisely, all of the objects manufactured by a class have the same memory layout and share a common set of methods). New classes can be defined in terms of existing classes through a technique known as inheritance. 

class method (Also known as factory method or constructor). A class method of class <X> is a method provided by the metaclass of class <X>. Class methods are executed without requiring any instances of class <X> to exist, and are frequently used to create instances. 

constructor See class method. 

dynamic method A method for which offset resolution is not available. 

factory method See class method. 

ID A pointer to a unique value that represents a string. 

inheritance The technique of specifying the shape and behavior of one class (called a subclass) as incremental differences from another class (called the parent class or superclass). The subclass inherits the superclass' state representation and methods, and can provide additional data elements and methods. The subclass also can provide new functions with the same method names used by the superclass. Such a subclass method is said to override the superclass method, and will be selected automatically by method resolution on subclass instances. An overriding method can elect to call upon the superclass' method as part of its own implementation. 

instance (Or object instance).  A specific object, as distinguished from the abstract definition of an object referred to as its class. 

instance method A method valid for a particular object. 

metaclass A class whose instances are all classes. In SOM, any class descended from SOMClass is a metaclass. The methods of a metaclass are sometimes called "class" methods (Smalltalk) or "factory" methods (Objective-C). 

method One of the units that makes up the behavior of an object. A method is a combination of a function and a name, such that many different functions can have the same name. Which function the name refers to at any point in time depends on the object that is to execute the method and is the subject of method resolution. Functions that have a common method name should also share a common signature. 

method resolution The process of selecting a particular function, given a method name and an object instance. The process results in selecting the particular function that implements the abstract method in a way appropriate for the designated object. SOM supports a variety of method-resolution mechanisms. 

object The elements of data and function that programs create, manipulate, pass as arguments, and so forth. An object is a way of associating specific data values with a specific set of named functions (called methods) for a period of time (referred to as the lifetime of the object). The data values of an object are referred to as its state. In SOM, objects are created by other objects called classes. The specification of what comprises the set of functions and data elements that make up an object is referred to as the definition of a class. 

SOM objects offer a high degree of encapsulation. This property permits many aspects of the implementation of an object to change without affecting client programs that depend on the object's behavior. 

object definition See class. 

object instance See instance. 

signature The collection of types associated with a method (the type of its return value, if any, as well as the number, order, and type of each of its arguments). All SOM methods that have the same name should also have the same signature. 

static method Any method that can be accessed through SOM offset resolution. 

subclass A class that inherits from another class. See inheritance. 

superclass A class from which another class inherits. See inheritance.
