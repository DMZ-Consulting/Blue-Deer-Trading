import os
import sys
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

# Get the absolute path of the current script
script_dir = os.path.dirname(os.path.abspath(__file__))
# Get the parent directory (project root)
project_root = os.path.dirname(script_dir)

# Change the working directory to the project root
os.chdir(project_root)

def run_migration(environment):
    # Use the correct path for alembic.ini
    alembic_cfg = Config(os.path.join(project_root, "alembic.ini"))
    alembic_cfg.set_main_option('environment', environment)

    try:
        # Get the ScriptDirectory
        script = ScriptDirectory.from_config(alembic_cfg)
        
        # Get all revisions
        revisions = list(script.walk_revisions("heads", base="base"))
        print(f"Total revisions found: {len(revisions)}")
        
        # Get current and head revisions
        current = command.current(alembic_cfg, verbose=True)
        head = revisions[0].revision if revisions else None

        print(f"Current revision: {current}")
        print(f"Head revision: {head}")

        if not head:
            print(f"No migration heads found for {environment}.")
            print("Available revisions:")
            for rev in revisions:
                print(f"  {rev.revision}: {rev.doc}")
            return

        if current == head:
            print(f"{environment.capitalize()} database is up to date.")
            return

        if current is None:
            print(f"No previous migrations found for {environment}. Stamping with head revision.")
            command.stamp(alembic_cfg, "head")
        else:
            print(f"Upgrading {environment} database from {current} to {head}")
            command.upgrade(alembic_cfg, "head")

        print(f"{environment.capitalize()} database migration complete.")

    except Exception as e:
        print(f"An error occurred during migration: {str(e)}")
        print("Make sure your alembic.ini file is correctly configured and your migration scripts are in the correct location.")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ['development', 'production']:
        print("Usage: python manage_migrations.py [development|production]")
        sys.exit(1)
    
    run_migration(sys.argv[1])
