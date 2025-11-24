from app.database import engine, Base
from app.models import AudioFile, AudioLineage

# This command looks at all the classes we imported (AudioFile, AudioLineage)
# and translates them into SQL "CREATE TABLE" commands.
print("Creating database tables...")
Base.metadata.create_all(bind=engine)
print("Tables created successfully!")