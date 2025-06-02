#!/usr/bin/env python
"""
Consolidated cleanup script to:
1. Fix import statements in the new directory structure
2. Remove redundant files from the root directory
"""
import os
import shutil
import sys

# Files to clean up from root directory (already moved to src structure)
root_files_to_remove = [
    'database_handler.py',
    'whisper_handler.py',
    'coqui_tts_handler.py',
    'fit_kit_db_handler.py', 
    'openai_handler.py',
    'audit_logger.py',
    'conversation_analyzer.py',
    'data_retention.py',
    'patient_routes.py',
    'app.py'
]

# Import mappings to update
import_mappings = {
    # Handlers
    'src/handlers/database_handler.py': [
        ('from audit_logger', 'from ..utils.audit_logger'),
        ('from data_retention', 'from ..utils.data_retention'),
    ],
    'src/handlers/fit_kit_db_handler.py': [
        ('from database_handler', 'from .database_handler'),
        ('from audit_logger', 'from ..utils.audit_logger'),
    ],
    'src/handlers/whisper_handler.py': [
        ('import openai', 'import openai'),  # Keep standard library imports as-is
    ],
    'src/handlers/coqui_tts_handler.py': [
        ('import openai', 'import openai'),  # Keep standard library imports as-is
    ],
    'src/handlers/openai_handler.py': [
        ('from database_handler', 'from .database_handler'),
    ],
    
    # Utils
    'src/utils/audit_logger.py': [
        ('from database_handler', 'from ..handlers.database_handler'),
    ],
    'src/utils/conversation_analyzer.py': [
        ('import openai', 'import openai'),  # Keep standard library imports as-is
        ('from database_handler', 'from ..handlers.database_handler'),
    ],
    'src/utils/data_retention.py': [
        ('from database_handler', 'from ..handlers.database_handler'),
        ('from audit_logger', 'from .audit_logger'),
    ],
    
    # Routes
    'src/routes/patient_routes.py': [
        ('from database_handler', 'from ..handlers.database_handler'),
        ('from audit_logger', 'from ..utils.audit_logger'),
        ('from fit_kit_db_handler', 'from ..handlers.fit_kit_db_handler'),
    ],
}

def clean_root_files():
    """Remove redundant files from root directory that have been moved to src structure"""
    print("Cleaning up redundant files from root directory...")
    cwd = os.getcwd()
    
    removed_count = 0
    for file_name in root_files_to_remove:
        file_path = os.path.join(cwd, file_name)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"✓ Removed {file_name}")
                removed_count += 1
            except Exception as e:
                print(f"✗ Failed to remove {file_name}: {e}")
                # Try to create a backup instead
                try:
                    backup_path = f"{file_path}.bak"
                    shutil.copy2(file_path, backup_path)
                    print(f"  Created backup at {backup_path}")
                except Exception as e2:
                    print(f"  Failed to create backup: {e2}")
        else:
            print(f"- {file_name} not found (already removed)")
    
    print(f"Removed {removed_count} of {len(root_files_to_remove)} redundant files")

def update_imports():
    """Update import statements in Python files"""
    print("Updating import statements...")
    cwd = os.getcwd()
    
    updated_count = 0
    for file_path, mappings in import_mappings.items():
        abs_path = os.path.join(cwd, file_path)
        if not os.path.exists(abs_path):
            print(f"File not found: {file_path}")
            continue
        
        # Read file content
        try:
            with open(abs_path, 'r') as f:
                content = f.read()
        except Exception as e:
            print(f"Failed to read {file_path}: {e}")
            continue
        
        # Apply import mappings
        modified = False
        for old_import, new_import in mappings:
            if old_import in content:
                content = content.replace(old_import, new_import)
                modified = True
        
        # Write updated content if modified
        if modified:
            try:
                with open(abs_path, 'w') as f:
                    f.write(content)
                print(f"✓ Updated imports in {file_path}")
                updated_count += 1
            except Exception as e:
                print(f"✗ Failed to update {file_path}: {e}")
        else:
            print(f"- No changes needed in {file_path}")
    
    print(f"Updated imports in {updated_count} files")

def clean_scripts_folder():
    """Clean up redundant scripts in the scripts folder"""
    print("Cleaning up redundant scripts...")
    cwd = os.getcwd()
    scripts_dir = os.path.join(cwd, "scripts")
    
    # Scripts to remove (keeping only cleanup.py and useful utilities)
    redundant_scripts = [
        "finalize_reorganization.py",
        "safe_reorganization.py", 
        "simple_reorganization.py",
        "update_imports.py"  # functionality now in cleanup.py
    ]
    
    removed_count = 0
    for script_name in redundant_scripts:
        script_path = os.path.join(scripts_dir, script_name)
        if os.path.exists(script_path):
            # Don't remove the current script
            if os.path.samefile(script_path, __file__):
                print(f"- Skipping current script: {script_name}")
                continue
                
            try:
                os.remove(script_path)
                print(f"✓ Removed redundant script: {script_name}")
                removed_count += 1
            except Exception as e:
                print(f"✗ Failed to remove {script_name}: {e}")
        else:
            print(f"- Script not found: {script_name}")
    
    print(f"Removed {removed_count} redundant scripts")

def clean_redundant_docs():
    """Clean up redundant documentation files"""
    print("Cleaning up redundant documentation files...")
    cwd = os.getcwd()
    
    # Files to remove
    redundant_docs = [
        "REORGANIZATION_STATUS.md",
        "REORGANIZATION_SIMPLE.md"
    ]
    
    removed_count = 0
    for doc_name in redundant_docs:
        doc_path = os.path.join(cwd, doc_name)
        if os.path.exists(doc_path):
            try:
                os.remove(doc_path)
                print(f"✓ Removed redundant doc: {doc_name}")
                removed_count += 1
            except Exception as e:
                print(f"✗ Failed to remove {doc_name}: {e}")
        else:
            print(f"- Doc not found: {doc_name}")
    
    print(f"Removed {removed_count} redundant docs")

def main():
    """Main function to clean up the project"""
    print("=== Starting Project Cleanup ===")
    
    # Update imports first
    update_imports()
    print()
    
    # Clean up root files
    clean_root_files()
    print()
    
    # Clean up scripts folder
    clean_scripts_folder()
    print()
    
    # Clean up redundant docs
    clean_redundant_docs()
    print()
    
    print("=== Project Cleanup Complete ===")
    print("1. Imports have been updated for the new directory structure")
    print("2. Redundant files have been removed from the root directory")
    print("3. Redundant scripts have been cleaned up")
    print("4. Next step: Try running the application with 'python run.py'")

if __name__ == "__main__":
    main()
