use spacetimedb::table;

#[table(accessor = build_runs, public)]
pub struct BuildRun {
    #[primary_key]
    pub id: u64,
    pub timestamp: u64,
    pub candidate_name: String,
    pub work_entries: u32,
    pub skills_count: u32,
    pub status: String, // "success" | "failure"
}

#[table(accessor = test_results, public)]
pub struct TestResult {
    #[primary_key]
    pub id: u64,
    pub build_run_id: u64,
    pub total: u32,
    pub passed: u32,
    pub failed: u32,
    pub duration_ms: u32,
}

#[table(accessor = schema_errors, public)]
pub struct SchemaError {
    #[primary_key]
    pub id: u64,
    pub build_run_id: u64,
    pub field_path: String,
    pub message: String,
}
