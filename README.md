# FreeCAD-Make

Build function for FreeCAD projects.
## Functions
### export-assemblies 
Exports all Shapes and TechDraw sheets linked to by an assembly to step files and pdfs.

## Features
+ Iterate through Assembly links and checks that the linked files are also being exported.
+ Export all

## Basic Function
+ Find all TechDrawings and export them to their own pdfs
    + A combined pdf can be made but should be done literally instead of automatically
+ Find all Parts and Bodies and export them to step files
+ File names should all have appropriate version and date codes.
