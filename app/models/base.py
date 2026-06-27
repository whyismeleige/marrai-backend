from sqlalchemy import MetaData

metadata = MetaData()

# Import all models over here so they register on metadata
# Add new model files here as you create them
from app.models import jobs
from app.models import users
from app.models import organizations
from app.models import organization_memberships
from app.models import brand_projects
from app.models import project_domains
from app.models import competitors
from app.models import competitor_domains
from app.models import prompt_sets
from app.models import prompts
from app.models import prompt_set_prompts
from app.models import ai_platforms
from app.models import run_batches
from app.models import prompt_runs
from app.models import ai_observations
from app.models import extraction_results
from app.models import citations
