from datetime import datetime
import os
from pathlib import Path
import shutil

IGNORE_DIRS = {
    '.git',
    'node_modules',
    '.next',
    '__pycache__',
    'dist',
    'build',
    'venv_build',
    'venv',
    'ZIP',
    '.venv',
}
IGNORE_FILES = {
    'package-lock.json',
    'generate_docs.py',
    'setup_structure.py',
    'README.md',
    'PROJECT_STRUCTURE.md',
    '.run_counter',
}
IGNORE_PREFIXES = {'STRUCTURE_RUN_'}
ALLOWED_EXTENSIONS = {
    '.ts',
    '.tsx',
    '.css',
    '.js',
    '.jsx',
    '.mjs',
    '.json',
    '.md',
    '.py',
    '.csv',
}

COUNTER_FILE = '.run_counter_zip'
ZIP_DIR = Path('ZIP')


def get_next_run_number():
  """Read current counter, increment, persist, and return the new value."""
  counter = 1
  if os.path.exists(COUNTER_FILE):
    try:
      with open(COUNTER_FILE, 'r') as f:
        counter = int(f.read().strip()) + 1
    except (ValueError, IOError):
      counter = 1
  with open(COUNTER_FILE, 'w') as f:
    f.write(str(counter))
  return counter


def should_ignore_file(filename, output_name):
  if filename == output_name or filename.startswith(output_name):
    return True
  if filename in IGNORE_FILES:
    return True
  if any(filename.startswith(p) for p in IGNORE_PREFIXES):
    return True
  return False


def get_user_choice():
  """Prompt user to choose between a full snapshot or specific targets."""
  print('Select snapshot mode:')
  print('1. Capture ENTIRE project contents')
  print(
      '2. Capture contents of SPECIFIC files/folders only (Tree view will still'
      ' show everything)'
  )

  choice = input('Enter choice (1 or 2): ').strip()

  if choice == '2':
    print('\nEnter relative paths to files or folders, separated by commas.')
    print('Example: src/utils, frontend/components/ui, app.py')
    user_input = input('Targets to include: ')

    raw_targets = []
    for t in user_input.split(','):
      cleaned = t.strip()
      if cleaned:
        raw_targets.append(Path(cleaned))
    return raw_targets, 'selective'
  return None, 'full'


def is_file_targeted(file_relative_path, target_paths):
  """Check if a file matches target individual files or lives inside target folders."""
  if target_paths is None:
    return True

  file_path_obj = Path(file_relative_path)

  for target in target_paths:
    if file_path_obj == target:
      return True
    try:
      if target.is_dir() or not target.suffix:
        if target in file_path_obj.parents:
          return True
    except Exception:
      if str(target) in str(file_path_obj):
        return True

  return False


def create_filtered_zip():
  # 1. Ask for Snapshot Mode & Scope Type
  target_paths, scope_type = get_user_choice()

  # 2. Ask for Snapshot Comment
  print('\n' + '=' * 40)
  snapshot_comment = input(
      'Enter snapshot comment/message (or press Enter to skip):\n> '
  ).strip()
  print('=' * 40)

  run_number = get_next_run_number()
  now = datetime.now()
  timestamp_str = now.strftime('%Y-%m-%d_%H-%M-%S')

  # Included scope_type ('full' or 'selective') directly in the base name
  base_name = f'CHEM-SYS-LAB-STRUCTURE_RUN_{run_number}_{scope_type}_{timestamp_str}'
  staging_dir = Path(base_name)
  ZIP_DIR.mkdir(parents=True, exist_ok=True)
  output_zip = ZIP_DIR / f'{base_name}.zip'

  # Create staging directory
  staging_dir.mkdir(parents=True, exist_ok=True)

  try:
    # 3. Write metadata info file inside the folder
    meta_file_path = staging_dir / 'SNAPSHOT_META.txt'
    with open(meta_file_path, 'w', encoding='utf-8') as meta:
      meta.write(f'Project Snapshot: {os.path.basename(os.getcwd())}\n')
      meta.write(f'Run Number: {run_number}\n')
      meta.write(f'Timestamp: {now.strftime("%B %d, %Y at %I:%M %p")}\n')
      meta.write(
          f'Scope: {scope_type.capitalize()}'
          f' {f"({len(target_paths)} targets)" if target_paths else ""}\n'
      )
      meta.write(f'Comment: {snapshot_comment or "No comment provided"}\n')

    copied_files_count = 0

    # 4. Walk through and copy matching files keeping relative directory structure
    for root, dirs, files in os.walk('.'):
      dirs[:] = sorted([d for d in dirs if d not in IGNORE_DIRS])

      for file in sorted(files):
        if should_ignore_file(file, base_name):
          continue
        lower_file = file.lower()
        if any(lower_file.endswith(ext.lower()) for ext in ALLOWED_EXTENSIONS):
          file_path = os.path.join(root, file)
          relative_path = os.path.relpath(file_path, '.')

          if not is_file_targeted(relative_path, target_paths):
            continue

          dest_path = staging_dir / relative_path
          dest_path.parent.mkdir(parents=True, exist_ok=True)

          shutil.copy2(file_path, dest_path)
          copied_files_count += 1

    # 5. Compress staging directory into a Zip file
    shutil.make_archive(
      str(output_zip.with_suffix('')),
      'zip',
      staging_dir.parent,
      staging_dir.name,
    )

    print(
        f'\n✅ Successfully zipped {copied_files_count} files into:'
        f' {output_zip}'
    )

  finally:
    if staging_dir.exists():
      shutil.rmtree(staging_dir)


if __name__ == '__main__':
  create_filtered_zip()
