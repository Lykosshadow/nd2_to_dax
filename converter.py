import glob
import numpy as np
import sys
import os
import nd2
import dask.array as da
from tqdm import trange

DEFAULT_BATCH_SIZE = 100

def convert_nd2_to_dax(nd2_path, dax_path,batch_size=DEFAULT_BATCH_SIZE):
    print(f"\nConverting ND2 to DAX: {nd2_path} → {dax_path}")
                
    try:
        from datawriter import DaxWriter  # Ensure this import works before proceeding

        # Open ND2 file and keep it open during frame access
        with nd2.ND2File(nd2_path) as f:
            print("ND2 shape:", f.shape)
            print("ND2 sizes:", f.sizes)
            
            dask_array = f.to_dask()
            shape = dask_array.shape

            # Handle different dimensionalities
            if len(shape) == 4:
                num_frames, num_channels, height, width = shape
                print(f"Detected 4D data: {num_frames} frames, {num_channels} channels, size {height}x{width}")
                
                if num_channels > 1:
                    print("Warning: Multiple channels detected. Defaulting to channel 0.")
                dask_array = dask_array[:, 0, :, :]  # Select channel 0
            
            elif len(shape) == 3:
                num_frames, height, width = shape
                print(f"Detected 3D data: {num_frames} frames, size {height}x{width}")
            
            elif len(shape) == 2:
                height, width = shape
                num_frames = 1
                print(f"Detected 2D data: single frame of size {height}x{width}")
                dask_array = dask_array.reshape((1, height, width))
            
            else:
                print(f"Unsupported ND2 shape: {shape}")
                return False

            print(f"Pixel dtype: {dask_array.dtype}")
            dax_file = DaxWriter(dax_path, width=width, height=height)

            for i in trange(0, num_frames, batch_size, desc="Converting frames"):
                end = min(i + batch_size, num_frames)
                try:
                    batch = dask_array[i:end].compute()  # shape: (B, H, W)
                    for frame in batch:
                        dax_file.addFrame(frame.astype(np.uint16))
                except Exception as e:
                    print(f"Error processing frames {i}–{end}: {e}")
                    dax_file.close()
                    return False

            dax_file.close()
            print(f"Successfully converted {nd2_path} to {dax_path}")
            return True

    except Exception as e:
        print(f"Conversion failed: {e}")
        return False


def main(nd2_folder, output_folder):
    if not os.path.isdir(nd2_folder):
        print(f"Folder not found: {nd2_folder}")
        sys.exit(1)

    nd2_files = sorted(glob.glob(os.path.join(nd2_folder, "*.nd2")))

    if not nd2_files:
        print("No ND2 files found.")
        sys.exit(1)

    dax_dir = os.path.join(output_folder, "dax_files")
    os.makedirs(dax_dir, exist_ok=True)

    for nd2_file in nd2_files:
        base_name = os.path.splitext(os.path.basename(nd2_file))[0]
        dax_path = os.path.join(dax_dir, base_name + ".dax")
        success = convert_nd2_to_dax(nd2_file, dax_path, batch_size=DEFAULT_BATCH_SIZE)

        if not success:
            print(f"Conversion failed for file: {nd2_file}")

    print("\n Batch conversion completed.")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python converter.py /path/to/nd2_files/ /path/to/output_folder/")
        sys.exit(1)

    nd2_folder = sys.argv[1]
    output_folder = sys.argv[2]
    main(nd2_folder, output_folder)
