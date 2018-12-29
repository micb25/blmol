# blmol: A script for importing molecular geometries into Blender  
  
blmol defines a molecule object that can be used to import molecular geometries (from a PDB file) into [Blender][]. It can be used to generate space filling, bond-only, and ball-and-stick models. The script includes definitions for simple default materials that can be used. These should be easily customized.  
  
## Installation  
  
Simply copy to Blender's scripts folder.  
  
## Usage  
  
Basic usage is to switch to the Scripting screen layout, then `import blmol`. Create a molecule object with `m = blmol.Molecule()`, then load the geometry with `m.read_pdb('path/to/file.pdb')`. A space filling model can be generated with `m.draw_atoms()` and a stick model with `m.draw_bonds()`. Many options can be changed as documented within the comments (more details to come here).  Please note that not all atom types are supported yet.

### Example
    import blmol
    m = blmol.Molecule()
    m.read_pdb('path/to/file.pdb')
    m.draw_bonds(radius=0.5)
  
[Blender]: http://www.blender.org
