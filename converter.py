import glob
import numpy as np
import sys
import os
import nd2 
import dask.array as da

def convert_nd2_to_dax(nd2_path, dax_path):
    print(f"Converting ND2 to DAX: {nd2_path} → {dax_path}")
                
    try:
        #Determine the dimensions of the files 
        with nd2.ND2File(nd2_path) as f:
            print(f.shape) # will print in format like (10,2,256,256)
            print(f.sizes) # will print in format like {'T':10, 'C': 2, 'Y':256, 'X':256}
            
            # Load lazily as dask array
            dask_array = f.to_dask() #this should be faster as it wont load all the image data
            shape = dask_array.shape
        
        if len(shape) == 4:
                # Shape e.g. (T, C, Y, X)
                num_frames, num_channels, height, width = shape
                print(f"4D data: {num_frames} frames, {num_channels} channels, {height}x{width} px")
                # Select channel 0 for conversion
                dask_array = dask_array[:, 0, :, :]
        elif len(shape) == 3:
            # Shape e.g. (T, Y, X)
            num_frames, height, width = shape
            print(f"3D data: {num_frames} frames, size {height}x{width} px")
        elif len(shape) == 2:
            # Single frame (Y, X)
            height, width = shape
            num_frames = 1
            print(f"2D single frame data, size {height}x{width} px")
            dask_array = dask_array.reshape((1, height, width))
        else:
            print(f"Unexpected ND2 data shape: {shape}")
            return False

    except Exception as e:
        print(f"Failed to read ND2 file {nd2_path}: {e}")
        return False
       
    try: 
        from datawriter import DaxWriter 
        dax_file = DaxWriter(dax_path, width=width, height=height)

        for i in range(num_frames):
            # Compute only one frame at a time (loads minimal data)
            frame = dask_array[i, :, :].compute()
            dax_file.addFrame(frame)    
        
        dax_file.close()
        print(f"Successfully converted {nd2_path} to {dax_path}")
        return True

    except Exception as e:
        print(f"Error writing DAX file {dax_path}: {e}")
        return False

    

def main(nd2_folder, output_folder):
    if not os.path.isdir(nd2_folder):
        print(f"Folder not found: {nd2_folder}")
        sys.exit(1)
    
    nd2_files = sorted(glob.glob(os.path.join(nd2_folder, "*.nd2")))

    if not nd2_files:
        print(f"No ND2 files found.")
        sys.exit(1)

    dax_dir = os.path.join(output_folder, "dax_files")
    os.makedirs(dax_dir, exist_ok=True)


    for nd2_file in nd2_files:
        base_name = os.path.splitext(os.path.basename(nd2_file))[0]
        dax_path = os.path.join(dax_dir, base_name + ".dax")
        success = convert_nd2_to_dax(nd2_file, dax_path)

        if not success:
            print(f"Conversion failed for file: {nd2_file}")

    print("Batch conversion completed.")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python converter.py /path/to/nd2_files/ /path/to/output_folder/")
        sys.exit(1)

    nd2_folder = sys.argv[1]
    output_folder = sys.argv[2]
    main(nd2_folder, output_folder)
