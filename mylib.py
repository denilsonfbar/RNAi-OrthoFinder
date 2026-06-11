import os
import sys
import subprocess
import zipfile
import shutil
from glob import glob
from datetime import datetime

def download_species_cds_and_proteome(species_list, output_folder):
    """
    Downloads both the CDS (Coding DNA Sequences) and Proteome (Protein sequences) 
    for a list of species from NCBI.
    
    Logic:
    1. Iterates through the provided list of species.
    2. Tries to find a RefSeq assembly.
    3. If not found, checks for GenBank assembly.
    4. Prompts the user based on availability (RefSeq vs GenBank vs None).
    5. Downloads, extracts, and renames the files:
       - CDS -> CDSs/{species_name}.fna
       - Proteome -> proteomes/{species_name}.faa
    
    Args:
        species_list: List of species.
        output_folder (str): Path to the destination root folder.
    """
    
    # 1. Setup Environment (Create folders)
    # Define subfolders for CDS and proteomes
    cds_folder = os.path.join(output_folder, "CDSs")
    prot_folder = os.path.join(output_folder, "proteomes")
    
    # Create the directories if they don't exist (exist_ok=True handles this cleanly)
    os.makedirs(cds_folder, exist_ok=True)
    os.makedirs(prot_folder, exist_ok=True)
        
    # --- MAIN LOOP ---
    for species_name in species_list:
        
        # Formatted species name for filenames (replace spaces with underscores)
        safe_name = species_name.replace(" ", "_")
        zip_path = os.path.join(output_folder, f"{safe_name}_temp.zip")
        temp_extract_dir = os.path.join(output_folder, f"temp_{safe_name}")

        # 2. Print Initial Log (Timestamp + Status)
        # end="" ensures the cursor stays on the same line to append "OK" later
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{current_time}] Downloading CDS and Proteome of {species_name}...", end="", flush=True)

        # 3. Check for RefSeq Availability using 'datasets summary'
        cmd_check_refseq = [
            "datasets", "summary", "genome", "taxon", species_name,
            "--assembly-source", "RefSeq",
            "--as-json-lines"
        ]
        
        # Run silently
        check_refseq = subprocess.run(cmd_check_refseq, capture_output=True, text=True)
        
        assembly_source = "RefSeq" # Default preference
        
        # If stdout is empty, RefSeq does not exist
        if not check_refseq.stdout.strip():
            
            # 3a. Check for GenBank Availability
            cmd_check_genbank = [
                "datasets", "summary", "genome", "taxon", species_name,
                "--as-json-lines"
            ]
            check_genbank = subprocess.run(cmd_check_genbank, capture_output=True, text=True)
            
            print("\n") # Move to next line to display the prompt clearly
            
            if check_genbank.stdout.strip():
                # Case: GenBank exists, but RefSeq does not
                print(f"   ⚠️  Warning: No RefSeq genome found for '{species_name}', but a GenBank assembly exists.")
                user_choice = input(f"   [1] Use GenBank assembly\n   [2] Skip this species\n   [3] Cancel pipeline\n   Select option: ")
                
                if user_choice == '1':
                    assembly_source = "GenBank"
                    # Reprint the status line so the final "OK" looks good
                    print(f"   Resuming download ({assembly_source})...", end="", flush=True)
                elif user_choice == '2':
                    print(f"   Skipping {species_name}.")
                    print("-" * 40)
                    continue # Skip to the next species in the loop
                else:
                    print("\nPipeline cancelled by user.")
                    sys.exit(1) # Stop the entire script
                    
            else:
                # Case: No genome found at all
                print(f"   ❌ Error: No genome found for '{species_name}' (neither RefSeq nor GenBank).")
                user_choice = input(f"   [1] Skip this species\n   [2] Cancel pipeline\n   Select option: ")
                
                if user_choice == '1':
                    print(f"   Skipping {species_name}.")
                    print("-" * 40)
                    continue # Skip to the next species
                else:
                    print("\nPipeline cancelled by user.")
                    sys.exit(1)

        # 4. Perform Download
        # Included 'protein' in the --include flag to fetch the proteome (.faa)
        cmd_download = [
            "datasets", "download", "genome", "taxon", species_name,
            "--assembly-source", assembly_source,
            "--include", "cds,protein",
            "--filename", zip_path
        ]
        
        try:
            # Run download (stderr piped to hide progress bar, ensuring clean output)
            subprocess.run(cmd_download, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            
            # 5. Process the Zip File
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_extract_dir)

            # Find the CDS and Protein files inside the extracted structure
            # Patterns match standard NCBI output
            found_cds = glob(os.path.join(temp_extract_dir, "ncbi_dataset", "data", "*", "*cds_from_genomic.fna"))
            found_prot = glob(os.path.join(temp_extract_dir, "ncbi_dataset", "data", "*", "*protein.faa"))

            # Error handling if files are missing from the zip
            if not found_cds:
                raise FileNotFoundError("CDS file not found inside the downloaded zip.")
            if not found_prot:
                raise FileNotFoundError("Protein file not found inside the downloaded zip.")
                
            cds_source = found_cds[0]
            prot_source = found_prot[0]
            
            # Destination paths updated to use the new subfolders
            cds_dest = os.path.join(cds_folder, f"{safe_name}.fna")
            prot_dest = os.path.join(prot_folder, f"{safe_name}.faa")
            
            # Move and Rename
            shutil.move(cds_source, cds_dest)
            shutil.move(prot_source, prot_dest)
            
            # 6. Success Output
            print(" OK")
            
        except subprocess.CalledProcessError:
            print(" FAILED")
            print(f"\n❌ Critical Error: Failed to download data for {species_name}.")
            sys.exit(1) 
        except Exception as e:
            print(" FAILED")
            print(f"\n❌ Error processing files: {e}")
            sys.exit(1)
        finally:
            # Cleanup temporary files
            if os.path.exists(zip_path):
                os.remove(zip_path)
            if os.path.exists(temp_extract_dir):
                shutil.rmtree(temp_extract_dir)