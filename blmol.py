"""
    Scripts for loading molecular geometries into Blender.

    Main use is to define the "molecule" object, which can be used to
    draw models of molecular coordinates.

    Written by Scott Hartley, www.hartleygroup.org and
    blog.hartleygroup.org.

    Hosted here:

    https://github.com/scotthartley/blmol

    Some aspects (especially rotating the bond cylinders) based on this
    wonderful blog post from Patrick Fuller:
    
    http://patrick-fuller.com/molecules-from-smiles-molfiles-in-blender/

    His project is hosted here:

    https://github.com/patrickfuller/blender-chemicals
    
    
    A few additions by Michael Böhme:
        - support of more elements
        - support of xyz files
        - balls and sticks drawing model via draw_balls_and_sticks()
        - error messages in read_pdb() and read_xyz() functions
    
    Improved version of blmol hosted here:
    https://github.com/micb25/blmol
        
"""

import numpy as np, time

# Python outside of Blender doesn't play all that well with bpy, so need
# to handle ImportError.
try:
    import bpy
    import bmesh
    bpy_avail = True
except ImportError:
    bpy_avail = False

# Dictionary of color definitions (RGB tuples). Blender RGB colors can
# be conveniently determined by using a uniform png of the desired color
# as a background image, then using the eyedropper. Colors with the
# "_cb" tag are based on colorblind-safe colors as described in this
# Nature Methods editorial DOI:10.1038/nmeth.1618.
COLORS = {
    'black': (0, 0, 0),
    'dark_red': (0.55, 0, 0),
    'gray': (0.2, 0.2, 0.2),
    'dark_gray': (0.1, 0.1, 0.1),
    'green': (0.133, 0.545, 0.133),
    'dark_green': (0.1, 0.5, 0.1),
    'indigo': (0.294, 0, 0.509),
    'light_gray': (0.7,0.7,0.7),
    'orange': (1.0, 0.647, 0),
    'purple': (0.627, 0.125, 0.941),
    'pink': (0.941, 0.561, 0.631),
    'cyan': (0.0, 1.000, 1.000),
    'red': (0.8, 0, 0),
    'royal_blue': (0.255, 0.412, 0.882),
    'white': (1.0, 1.0, 1.0),
    'yellow': (1.0, 1.0, 0),
    'blue_cb': (0, 0.168, 0.445),
    'bluish_green_cb': (0, 0.620, 0.451),
    'orange_cb': (0.791, 0.347, 0),
    'reddish_purple_cb': (0.800, 0.475, 0.655),
    'sky_blue_cb': (0.337, 0.706, 0.914),
    'vermillion_cb': (0.665, 0.112, 0),
    'yellow_cb': (0.871, 0.776, 0.054)
    }

ATOMIC_NUMBERS = {
    'H': 1,
    'HE': 2,
    'LI': 3,
    'BE': 4,
    'B': 5,
    'C': 6,
    'N': 7,
    'O': 8,
    'F': 9,
    'NE': 10,
    'NA': 11,
    'MG': 12,
    'AL': 13,
    'SI': 14,
    'P': 15,
    'S': 16,
    'CL': 17,
    'AR': 18,
    'K': 19,
    'CA': 20,
    'SC': 21,
    'TI': 22,
    'V': 23,
    'CR': 24,
    'MN': 25,
    'FE': 26,
    'CO': 27,
    'NI': 28,
    'CU': 29,
    'ZN': 30,
    'GA': 31,
    'GE': 32,
    'AS': 33,
    'SE': 34,
    'BR': 35,
    'KR': 36,
    'I': 53
    }

# Dictionary of Van der Waals radii, by atomic number, from Wolfram
# Alpha and Open Babel.
RADII = { 
    1: 1.20,
    2: 1.40,
    3: 1.81,
    4: 1.53,
    5: 1.92, # From wikipedia
    6: 1.70,
    7: 1.55,
    8: 1.52,
    9: 1.47,
    10: 1.54,
    11: 2.27,
    12: 1.73, # From wikipedia
    13: 1.84,
    14: 2.10,
    15: 1.80,
    16: 1.80,
    17: 1.75,
    18: 1.88,
    19: 2.75,
    20: 2.31,
    21: 2.30,
    22: 2.15,
    23: 2.05,
    24: 2.05,
    25: 2.05,
    26: 2.05,
    27: 2.00,
    28: 2.00,
    29: 2.00,
    30: 1.39, # From wikipedia
    31: 1.87,
    32: 2.11,
    33: 1.85,
    34: 1.90,
    35: 1.83,
    36: 2.02,
    53: 1.98
    }

# Dictionaries of colors for drawing elements, by atomic number. Used by
# several functions when the `color = 'by_element'` option is passed.
ELEMENT_COLORS = { 
    1: 'white',
    2: 'white',
    3: 'dark_gray',
    4: 'dark_gray',
    5: 'orange',
    6: 'gray',
    7: 'royal_blue',
    8: 'red',
    9: 'green',
    10: 'dark_gray',
    11: 'dark_gray',
    12: 'dark_green',
    13: 'dark_gray',
    14: 'dark_gray',
    15: 'orange',
    16: 'yellow',
    17: 'green',
    18: 'dark_gray',
    19: 'dark_gray',
    20: 'dark_gray',
    21: 'dark_gray',
    22: 'dark_gray',
    23: 'dark_gray',
    24: 'dark_gray',
    25: 'dark_gray',
    26: 'dark_gray',
    27: 'purple',
    28: 'dark_gray',
    29: 'cyan',
    30: 'dark_gray',
    31: 'dark_gray',
    32: 'dark_gray',
    33: 'dark_gray',
    34: 'dark_gray',
    35: 'dark_red',
    36: 'dark_gray',
    53: 'indigo'
    }

# Conversion factors for 1 BU. Default is typically 1 nm. Assumes
# geometries are input with coords in angstroms.
UNIT_CONV = { 
    'nm': 0.1,
    'A': 1.0 
    }

def _create_new_material(name, color):
    """Create a new material.

    Args:
        name (str): Name for the new material (e.g., 'red')
        color (tuple): RGB color for the new material (diffuse_color) 
            (e.g., (1, 0, 0))
    Returns:
        The new material.
    """
    
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = color
    mat.diffuse_shader = 'OREN_NAYAR'
    mat.diffuse_intensity = 0.8
    mat.roughness = 0.5
    mat.specular_color = (1, 1, 1)
    mat.specular_shader = 'BLINN'
    mat.specular_intensity = 0.2
    mat.specular_hardness = 25
    mat.ambient = 1
    mat.use_transparent_shadows = True
    # mat.subsurface_scattering.use = True

    return mat


class Atom:
    """A single atom.

    Attributes:
        at_num (int): The atomic number of the atom.
        location (numpy array): The xyz location of the atom, in 
            Angstroms.
        id_num (int): A unique identifier number.
    """

    def __init__(self, atomic_number, location, id_num):
        self.at_num = atomic_number
        self.location = location # np.array
        self.id_num = id_num

    def draw(self, color='by_element', radius=None, units='nm', 
             scale=1.0, subsurf_level=2, segments=32):
        """Draw the atom in Blender.

        Args:
            color (string, ='by_element'): If None, coloring is done by
                element. Otherwise specifies the color.
            radius (string, =None): If None, draws at the van der Waals
                radius. Otherwise specifies the radius in angstroms.
            units (sting, ='nm'): 1 BU = 1 nm by default. Can also be
                set to angstroms.
            scale (float, =1.0): Scaling factor for the atom. Useful
                when generating ball-and-stick models.
            subsurf_level (int, =2): Subsurface subdivisions that will
            	be applied.
            segments (int, =32): Number of segments in each UV sphere
                primitive

        Returns:
            The blender object.
        """

        # The corrected location (i.e., scaled to units.)
        loc_corr = tuple(c*UNIT_CONV[units] for c in self.location)

        # Work out the sphere radius in BU.
        if not radius:
            rad_adj = RADII[self.at_num]*UNIT_CONV[units]*scale
        else:
            rad_adj = radius*UNIT_CONV[units]*scale

        # Create sphere as bmesh.
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, 
                                  u_segments=segments, 
                                  v_segments=segments,
                                  diameter=rad_adj)
        
        for f in bm.faces:
            f.smooth = True
        
        # Convert to mesh.
        me = bpy.data.meshes.new("Mesh")
        bm.to_mesh(me)
        bm.free()

        # Assign mesh to object and place in space.
        atom_sphere = bpy.data.objects.new("atom({})_{}".format(
                            self.at_num, self.id_num), me)
        bpy.context.scene.objects.link(atom_sphere)
        
        atom_sphere.location = loc_corr

        # Assign subsurface modifier, if requested
        if subsurf_level != 0:
            atom_sphere.modifiers.new('Subsurf', 'SUBSURF')
            atom_sphere.modifiers['Subsurf'].levels = subsurf_level

        # Color atom and assign material
        if color == 'by_element':
            atom_color = ELEMENT_COLORS[self.at_num]
        else:
            atom_color = color

        if not atom_color in bpy.data.materials:
            _create_new_material(atom_color, COLORS[atom_color])

        atom_sphere.data.materials.append(bpy.data.materials[atom_color])

        return atom_sphere


class Bond:
    """A bond between two atoms.

    Attributes:
        atom1 (atom): The first atom in the bond.
        atom2 (atom): The second atom in the bond.
    """

    def __init__(self, atom1, atom2):
        self.atom1 = atom1
        self.atom2 = atom2

    @staticmethod
    def _draw_half(location, length, rot_angle, rot_axis, element, 
                   radius=0.2, color='by_element', units='nm',
                   vertices=64, edge_split=False):
        """Draw half of a bond (static method).

        Draws half of a bond, given the location and length. Bonds are
        drawn in halves to facilitate coloring by element.

        Args:
            location (np.array): The center point of the half bond.
            length (float): The length of the half bond.
            rot_angle (float): Angle by which bond will be rotated.
            rot_axis (np.array): Axis of rotation.
            element (int): atomic number of element of the bond (for 
                coloring).
            radius (float, =0.2): radius of the bond.
            color (string, ='by_element'): color of the bond. If
                'by_element', uses element coloring.
            units (string, ='nm'): 1 BU = 1 nm, by default. Can change
                to angstroms ('A').
            vertices (int, =64): Number of vertices in each bond
                cylinder.
            edge_split (bool, =False): Whether to apply the edge split
                modifier to each bond.

        Returns:
            The new bond (Blender object).
        """

        loc_corr = tuple(c*UNIT_CONV[units] for c in location)
        len_corr = length * UNIT_CONV[units]
        radius_corr = radius * UNIT_CONV[units]

        bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,
                                            radius=radius_corr, 
                                            depth=len_corr, location=loc_corr, 
                                            end_fill_type='NOTHING')
        bpy.ops.transform.rotate(value=rot_angle, axis=rot_axis)
        bpy.ops.object.shade_smooth()

        if edge_split:
            bpy.ops.object.modifier_add(type='EDGE_SPLIT')
            bpy.ops.object.modifier_apply(modifier='EdgeSplit')

        if color == 'by_element':
            bond_color = ELEMENT_COLORS[element]
        else:
            bond_color = color

        if not bond_color in bpy.data.materials:
            _create_new_material(bond_color, COLORS[bond_color])

        bpy.context.object.data.materials.append(
            bpy.data.materials[bond_color])

        return bpy.context.object


    def draw(self, radius=0.2, color='by_element', units='nm',
             vertices=64, edge_split=False):
        """Draw the bond as two half bonds (to allow coloring).

        Args:
            radius (float, =0.2): Radius of cylinder in angstroms.
            color (string, ='by_element'): Color of the bond. If
                'by_element', each half gets element coloring.
            units (string, ='nm'): 1 BU = 1 nm, by default. Can change
                to angstroms ('A').
            vertices (int, =64): Number of vertices in each bond
                cylinder.
            edge_split (bool, =False): Whether to apply the edge split
                modifier to each bond.

        Returns:
            The bond (Blender object), with both halves joined.
        """

        created_objects = []

        center_loc = (self.atom1.location + self.atom2.location)/2
        bond_vector = self.atom1.location - self.atom2.location
        length = np.linalg.norm(bond_vector)

        bond_axis = bond_vector/length
        cyl_axis = np.array((0,0,1))
        rot_axis = np.cross(bond_axis, cyl_axis)
        angle = -np.arccos(np.dot(cyl_axis, bond_axis))

        start_center = (self.atom1.location + center_loc)/2
        created_objects.append(Bond._draw_half(start_center, length/2, angle, 
                               rot_axis, self.atom1.at_num, radius, color, 
                               units, vertices, edge_split))

        end_center = (self.atom2.location + center_loc)/2
        created_objects.append(Bond._draw_half(end_center, length/2, angle, 
                               rot_axis, self.atom2.at_num, radius, color, 
                               units, vertices, edge_split))

        for obj in bpy.context.selected_objects:
            obj.select = False

        for obj in created_objects:
            obj.select = True

        bpy.ops.object.join()
        bpy.context.object.name = "bond_{}({})_{}({})".format(
            self.atom1.id_num, self.atom1.at_num, self.atom2.id_num, 
            self.atom2.at_num)
        
        return bpy.context.object


class Molecule:
    """The molecule object.

    Attributes:
        atoms (list, = []): List of atoms (atom objects) in molecule.
        bonds (list, = []): List of bonds (bond objects) in molecule.
    """

    def __init__(self, name='molecule', atoms=None, bonds=None):
        self.name = name
        if atoms == None:
            self.atoms = []
        else:
            self.atoms = atoms
        if bonds == None:
            self.bonds = []
        else:
            self.bonds = bonds
    
    def add_atom(self, atom):
        """Adds an atom to the molecule."""
        self.atoms.append(atom)

    def add_bond(self, a1id, a2id):
        """Adds a bond to the molecule, using atom ids."""
        if not self.search_bondids(a1id, a2id):
            self.bonds.append(Bond(self.search_atomid(a1id), 
                                   self.search_atomid(a2id)))

    def search_atomid(self, id_to_search):
        """Searches through atom list and returns atom object
        corresponding to (unique) id."""
        for atom in self.atoms:
            if atom.id_num == id_to_search:
                return atom
        return None

    def search_bondids(self, id1, id2):
        """Searches through bond list and returns bond object
        corresponding to (unique) ids."""
        for b in self.bonds:
            if ((id1, id2) == (b.atom1.id_num, b.atom2.id_num) or
                    (id2, id1) == (b.atom1.id_num, b.atom2.id_num)):
                return b
        return None

    def draw_bonds(self, caps=True, radius=0.2, color='by_element', 
                   units='nm', join=True, with_H=True, subsurf_level=1,
                   vertices=64, edge_split=False):
        """Draws the molecule's bonds.

        Args:
            caps (bool, =True): If true, each bond capped with sphere of
                radius at atom position. Make false if drawing
                ball-and-stick model using separate atom drawings.
            radius (float, =0.2): Radius of bonds in angstroms.
            color (string, ='by_element'): Color of the bonds. If
                'by_element', each gets element coloring.
            units (string, ='nm'): 1 BU = 1 nm, by default. Can change
                to angstroms ('A').
            join (bool, =True): If true, all bonds are joined together
                into a single Bl object.
            with_H (bool, =True): Include H's.
            subsurf_level (int, =1): Subsurface subdivisions that will
            	be applied to the atoms (end caps).
            vertices (int, =64): Number of vertices in each bond
                cylinder.
            edge_split (bool, =False): Whether to apply the edge split
                modifier to each bond.

        Returns:
            The bonds as a single Blender object, if join=True.
            Otherwise, None.
        """
        
        created_objects = []

        for b in self.bonds:
            if with_H or ( b.atom1.at_num != 1 and b.atom2.at_num != 1 ):
                created_objects.append(b.draw(radius=radius,
                                              color=color, 
                                              units=units, 
                                              vertices=vertices,
                                              edge_split=edge_split))

        if caps:
            for a in self.atoms:
                if with_H or a.at_num != 1:
                    created_objects.append(a.draw(color=color, 
                                                  radius=radius, 
                                                  units=units,
                                                  subsurf_level=subsurf_level))
        
        if join:
            # Deselect anything currently selected.
            for obj in bpy.context.selected_objects:
                obj.select = False

            # Select drawn bonds.
            for obj in created_objects:
                obj.select = True

            bpy.ops.object.join()

            bpy.context.object.name = self.name + '_bonds'
            
            return bpy.context.object

        else:
            return None


    def draw_atoms(self, color='by_element', radius=None, units='nm', 
                   scale=1.0, join=True, with_H=True, subsurf_level=2,
                   segments=16):
        """Draw spheres for all atoms.

        Args: 
            color (str, ='by_element'): If 'by_element', uses colors in
                ELEMENT_COLORS. Otherwise, can specify color for whole
                model. Must be defined in COLORS.
            radius (float, =None): If specified, gives radius of all 
                atoms.
            units (str, ='nm'): Units for 1 BU. Can also be A.
            join (bool, =True): If true, all atoms are joined together
                into a single Bl object.
            with_H (bool, =True): Include the hydrogens.
            subsurf_level (int, =2): Subsurface subdivisions that will
            	be applied to the atoms.
            segments (int, =16): Number of segments in each UV sphere
                primitive

        Returns:
            The atoms as a single Blender object, if join=True.
            Otherwise, None.
        """

        # Store start time to time script.
        start_time = time.time()

        # Holds links to all created objects, so that they can be
        # joined.
        created_objects = []

        # Initiate progress monitor over mouse cursor.
        bpy.context.window_manager.progress_begin(0, len(self.atoms))
        
        n = 0
        for a in self.atoms:
            if with_H or a.at_num != 1:
                created_objects.append(a.draw(color=color, radius=radius, 
                                              units=units, scale=scale,
                                              subsurf_level=subsurf_level,
                                              segments=segments))
            n += 1
            bpy.context.window_manager.progress_update(n)

        # End progress monitor.
        bpy.context.window_manager.progress_end()

        if join:
            # Deselect all objects in scene.
            for obj in bpy.context.selected_objects:
                obj.select = False
            # Select all newly created objects.
            for obj in created_objects:
                obj.select = True
            bpy.context.scene.objects.active = created_objects[0]
            bpy.ops.object.join()
            bpy.context.object.name = self.name + '_atoms'
            
        print("{} seconds".format(time.time()-start_time))
        return
    
        
    def draw_ball_and_stick(self, color='by_element', units='nm', join=True,
                              with_H=True):
        
        self.draw_atoms(scale=0.25, color=color, units=units, join=join, with_H=with_H)
        self.draw_bonds(radius=0.15, color=color, units=units, join=join, with_H=with_H)


    def read_pdb(self, filename):
        """
        Loads a .pdb file into a molecule object. Only accepts atoms
        with Cartesian coords through the ATOM/HETATM label and bonds
        through the CONECT label.

        Args:
            filename (string): The target file.
        """

        try:
            with open(filename) as pdbfile:
                for line in pdbfile:
                    if line[0:4] == "ATOM":
                        idnum = int(line[6:11])
                        atnum = ATOMIC_NUMBERS[line[76:78].strip().upper()]
                        coords = np.array((float(line[30:38]), float(line[38:46]), 
                                           float(line[46:54])))
                        self.add_atom(Atom(atnum, coords, idnum))
    
                    elif line[0:6] == "HETATM":
                        idnum = int(line[6:11])
                        atnum = ATOMIC_NUMBERS[line[76:78].strip().upper()]
                        coords = np.array((float(line[30:38]), float(line[38:46]), 
                                           float(line[46:54])))
                        self.add_atom(Atom(atnum, coords, idnum))
    
                    elif line[0:6] == "CONECT":
    
                        # Loads atoms as a list. First atom is bonded to the
                        # remaining atoms (up to four).
                        atoms = line[6:].split()
                        for bonded_atom in atoms[1:]:
                            self.add_bond(int(atoms[0]), int(bonded_atom))
        except:
            print("Error while reading .pdb file!")
            

    def read_xyz(self, filename):
        """
        Loads an .xyz file into a molecule object. Since these files do not
        contain bond information the bonds need to be calculated, e.g. based 
        on their Van der Waals radii.

        Args:
            filename (string): The target file.
        """

        try:
            # read atoms
            with open(filename) as xyzfile:
                line = xyzfile.readline()
                natoms = int(line)
                idnum = 0
                if ( natoms > 0 ):
                    # skip the comment line
                    line = xyzfile.readline()
                    for line in xyzfile:
                        ls = line.strip().upper().split()
                        idnum += 1
                        atnum = ATOMIC_NUMBERS[ls[0]]
                        coords = np.array((float(ls[1]), float(ls[2]), 
                                           float(ls[3])))
                        self.add_atom(Atom(atnum, coords, idnum))
                        
                        # break here (trajectory files might contain more data)
                        if ( idnum >= natoms ):
                            break;
                        
            # calculate bonds -- quick'n'dirty
            for i in range(0, len(self.atoms)):
                for j in range(0, i):
                    bdist = ( RADII[self.atoms[i].at_num] + RADII[self.atoms[j].at_num] ) / 2.0
                    rdist = ((self.atoms[i].location[0] - self.atoms[j].location[0])**2.0 + 
                             (self.atoms[i].location[1] - self.atoms[j].location[1])**2.0 + 
                             (self.atoms[i].location[2] - self.atoms[j].location[2])**2.0 )**0.5
                    
                    # there might be better ways
                    if ( rdist < bdist ):
                        self.add_bond(self.atoms[i].id_num, self.atoms[j].id_num)
                
        except:
            print("Error while reading .xyz file!")
            
