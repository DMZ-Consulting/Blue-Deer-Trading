import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base, engine, get_database_url
from app.models import TradeConfiguration, VerificationConfig

def init_db():
    db_url = get_database_url()
    print(f"Database URL: {db_url}")
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()

    # Check if we're using the local.db file
    if os.path.basename(db_url.replace('sqlite:///', '')) == 'local.db':
        # Add default trade configurations
        default_configs = [
            TradeConfiguration(
                name="day_trader",
                channel_id="1284992080254599269",
                role_id="1283513057620004954",
                roadmap_channel_id="1284992080254599269",
                update_channel_id="1284992080254599269",
                portfolio_channel_id="1284992080254599269",
                log_channel_id="1284992080254599269"
            ),
            TradeConfiguration(
                name="swing_trader",
                channel_id="1284992128723980360",
                role_id="1283513079979708507",
                roadmap_channel_id="1284992128723980360",
                update_channel_id="1284992128723980360",
                portfolio_channel_id="1284992128723980360",
                log_channel_id="1284992128723980360"
            ),
            TradeConfiguration(
                name="long_term_trader",
                channel_id="1284992206633046071",
                role_id="1283513098430320700",
                roadmap_channel_id="1284992206633046071",
                update_channel_id="1284992206633046071",
                portfolio_channel_id="1284992206633046071",
                log_channel_id="1284992206633046071"
            )
        ]

        default_verification_config = VerificationConfig(
            message_id="1294025725699166249",
            role_to_remove_id="1258466163722158173",
            role_to_add_id="1258466163722158173",
            channel_id="1108449289790824481",
            log_channel_id="1222627917511655607"
        )

        # Check if configurations already exist
        existing_configs = db.query(TradeConfiguration).all()
        existing_names = set(config.name for config in existing_configs)

        # Add only the configurations that don't already exist
        for config in default_configs:
            if config.name not in existing_names:
                db.add(config)

        db.add(default_verification_config)

        db.commit()

    db.close()

if __name__ == "__main__":
    init_db()