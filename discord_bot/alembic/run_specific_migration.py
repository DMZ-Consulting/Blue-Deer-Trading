import sys
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine
from alembic.runtime.migration import MigrationContext

def run_specific_migration(revision):
    alembic_cfg = Config("alembic.ini")
    script = ScriptDirectory.from_config(alembic_cfg)
    engine = create_engine(alembic_cfg.get_main_option("sqlalchemy.url"))

    # Check current revision
    with engine.connect() as conn:
        context = MigrationContext.configure(conn)
        current_rev = context.get_current_revision()

    if current_rev is None:
        # If no revision is set, stamp the baseline
        baseline_rev = script.get_base()
        if baseline_rev is None:
            print("No baseline revision found. Starting from the beginning.")
            current_rev = None
        else:
            baseline_rev = baseline_rev.revision if hasattr(baseline_rev, 'revision') else baseline_rev
            command.stamp(alembic_cfg, baseline_rev)
            print(f"Stamped baseline revision: {baseline_rev}")
            current_rev = baseline_rev

    # Get all revisions between current and target
    revisions = list(script.iterate_revisions(current_rev, revision))
    
    for rev in revisions:
        try:
            command.upgrade(alembic_cfg, rev.revision)
            print(f"Upgraded to revision: {rev.revision}")
        except Exception as e:
            print(f"Error applying revision {rev.revision}: {str(e)}")
            print("Continuing to next revision...")

    print(f"Migration process completed.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python run_specific_migration.py <revision>")
        sys.exit(1)
    run_specific_migration(sys.argv[1])
