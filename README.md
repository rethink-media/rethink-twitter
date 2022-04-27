# rethink-twitter
Repository for ReThink Media's Twitter API, built to analyze 9/11 anniversary coverage and then expanded for more general use.
Objectives include:
- Search for Tweets relevant to a query within the past 7 days, the past 30 days, and the full Tweet archive
- Filter for the top influencers for a specific query
- Create word clouds from word and hashtag counts in tweets
- Plot the volume of relevant Tweets over time

The main notebooks to use in the `notebooks/` directory are `ReThink Twitter API User Guide.ipynb` (this notebook includes full docstrings for the analysis and datavis functions) and `ReThink Twitter API User Template.ipynb` (this notebook is built to work out-of-the-box for specific queries). To use the notebooks, the user must have a `.env` file with a Twitter API keys defined within the working environment. The necessary Twitter API keys are: 
- `API_KEY`
- `API_KEY_SECRET`
- `BEARER_TOKEN`
- `ACCESS_TOKEN`
- `ACCESS_SECRET`
