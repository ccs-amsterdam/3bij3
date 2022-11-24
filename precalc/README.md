# Precalc folder

To enhance performance, 3bij3 precalculates metrics such as article similarities (or, in some configurations, also topics based on ML models) and inserts them into the database. This has the advantage that these (time-consuming) operations do not have to be done when a user requests a page.