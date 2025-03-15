# FreeCAD-Make

Build function for FreeCAD projects. This is focused on making it easy to issue Releases from FreeCAD Assemblies and a collection of FreeCAD files. This is similar in spirit to my kicad-make project [here](www.github.com/snhobbs/kicad-make).

## Functions
### check-links
Assemblies are comprised of linked objects. When building a project it is good to know you're linking to the files you think you are. This function returns successfully if all the interal linked objects are files that are currently in the build command. Use this to check an entire directory of FreeCAD files.

## export-object
Export a specific named object from a file. This is slower but is useful in a Makefile.

## export
This is the main heavy lifter and has several options.
By default all the Assembies are crawled for links and then each of the files has a directory that all the parts are exported to. PDFs and step files are generated. All the files can be exported to a single directory instead with --single-directory.
If you only care about the objects in a single Part or Assembly then you can use --single-ile which will put all the linked objects of a given parent in the same directory.
If multiple files linking the same objects are passed then there will be duplication in this mode.
Use --pdf-only to skip the step files and only export the TechDraw pages as PDFs.


## Features
+ Export all TechDraw pages from a list of files
+ Crawl Assembly link trees to ensure the links are within known files
+ Export all the related components of a project with consistant naming and organization.

