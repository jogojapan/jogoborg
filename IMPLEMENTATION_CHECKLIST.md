# Jogoborg Local Testing - Implementation Checklist

## Overview

This checklist guides you through implementing and validating the local testing environment.

---

## Phase 1: Initial Setup ✅ COMPLETE

### Files Created
- [x] `local_test/` directory
- [x] `local_test/setup.sh` - Initialize environment
- [x] `local_test/run_local.sh` - Start services
- [x] `local_test/stop_local.sh` - Stop services
- [x] `local_test/reset_test_data.sh` - Reset to clean state
- [x] `local_test/dev_helpers.sh` - Development helpers
- [x] `local_test/Makefile` - Make commands
- [x] `local_test/env.local.example` - Configuration template
- [x] `local_test/README.md` - Setup guide
- [x] `local_test/TESTING_GUIDE.md` - Test scenarios
- [x] `local_test/QUICK_REFERENCE.md` - Quick reference
- [x] `LOCAL_TESTING_SETUP.md` - Complete guide
- [x] `TESTING_APPROACH.md` - Testing strategy
- [x] `TESTING_SUMMARY.md` - Executive summary

### Documentation Created
- [x] Project analysis
- [x] Architecture overview
- [x] Testing approach
- [x] Quick start guide
- [x] Detailed testing guide
- [x] Troubleshooting guide
- [x] Performance expectations
- [x] Integration guide

---

## Phase 2: Validation (Next Steps)

### Python Virtual Environment Setup (Recommended)
- [ ] Create virtual environment: `python3 -m venv venv`
- [ ] Activate virtual environment: `source venv/bin/activate`
- [ ] Verify activation (should see `(venv)` in prompt)

### Prerequisites Check
- [ ] Python 3.7+ installed
- [ ] SQLite 3 installed
- [ ] Borg Backup installed
- [ ] GPG installed
- [ ] Required Python packages available

**Validation Command:**
```bash
cd local_test
make check-deps
```

### Virtual Environment Activation
- [ ] From project root, create venv: `python3 -m venv venv`
- [ ] Activate venv: `source venv/bin/activate`
- [ ] Verify `(venv)` appears in prompt

### Initial Setup
- [ ] Navigate to `local_test` directory
- [ ] Run `./setup.sh`
- [ ] Verify no errors
- [ ] Check directories created:
  - [ ] `config/` directory exists
  - [ ] `borgspace/` directory exists
  - [ ] `logs/` directory exists
  - [ ] `sourcespace/` directory exists
- [ ] Check files created:
  - [ ] `config/jogoborg.db` exists
  - [ ] `config/jogoborg.gpg` exists
  - [ ] `env.local` exists
- [ ] Check sample data:
  - [ ] `sourcespace/sample_data/file1.txt` exists
  - [ ] `sourcespace/sample_data/file2.txt` exists
  - [ ] `sourcespace/sample_data/nested/file3.txt` exists
  - [ ] `sourcespace/sample_data/large_file.bin` exists (10MB)

**Validation Command:**
```bash
cd local_test
ls -la config/
ls -la borgspace/
ls -la logs/
ls -la sourcespace/sample_data/
```

### Configuration Review
- [ ] Review `env.local`
- [ ] Verify web port (default: 8080)
- [ ] Verify username (default: testuser)
- [ ] Verify password (default: testpass123)
- [ ] Verify GPG passphrase set
- [ ] Verify all paths are correct

**Validation Command:**
```bash
cat env.local
```

### Service Startup
- [ ] Run `./run_local.sh`
- [ ] Verify no errors
- [ ] Check web server started:
  - [ ] `logs/web_server.log` created
  - [ ] No errors in log
- [ ] Check scheduler started:
  - [ ] `logs/scheduler.log` created
  - [ ] No errors in log
- [ ] Verify services running:
  - [ ] `ps aux | grep python3` shows 2 processes
  - [ ] `.web_server.pid` file exists
  - [ ] `.scheduler.pid` file exists

**Validation Commands:**
```bash
make status
ps aux | grep python3
tail logs/web_server.log
tail logs/scheduler.log
```

### Web UI Access
- [ ] Open browser: http://localhost:8080
- [ ] Page loads without errors
- [ ] Login form appears
- [ ] Login with credentials from `env.local`
- [ ] Dashboard loads
- [ ] No console errors (F12)

**Validation:**
- Visual inspection in browser
- Check browser console (F12) for errors

### API Health Check
- [ ] Run `make api-health`
- [ ] API responds with health status
- [ ] No connection errors

**Validation Command:**
```bash
make api-health
```

---

## Phase 3: Basic Testing

### Test 1: Create Backup Job
- [ ] Access web UI
- [ ] Click "New Job"
- [ ] Fill in form:
  - [ ] Name: `test-backup-1`
  - [ ] Schedule: `0 * * * *`
  - [ ] Source: `sourcespace/sample_data`
  - [ ] Compression: `lz4`
- [ ] Click "Create"
- [ ] Job appears in list

**Validation Commands:**
```bash
make db-jobs
sqlite3 config/jogoborg.db "SELECT name FROM backup_jobs;"
```

### Test 2: Manual Job Execution
- [ ] Click "Run Now" on job
- [ ] Wait for execution
- [ ] Check logs: `make logs-scheduler`
- [ ] Verify job completed
- [ ] Check database: `make db-logs`

**Validation Commands:**
```bash
make logs-scheduler
make db-logs
make repos
```

### Test 3: Repository Verification
- [ ] Check repository created: `make repos`
- [ ] Verify repository size: `make repos-size`
- [ ] List repository contents: `borg list borgspace/test-backup-1`

**Validation Commands:**
```bash
ls -la borgspace/
du -sh borgspace/*
borg list borgspace/test-backup-1
```

### Test 4: Log Verification
- [ ] Check web server logs: `make logs-show-web`
- [ ] Check scheduler logs: `make logs-show-scheduler`
- [ ] Verify no errors
- [ ] Verify job execution recorded

**Validation Commands:**
```bash
cat logs/web_server.log
cat logs/scheduler.log
grep -i "error" logs/*.log
```

### Test 5: Database Verification
- [ ] Query backup jobs: `make db-jobs`
- [ ] Query job logs: `make db-logs`
- [ ] Verify data consistency

**Validation Commands:**
```bash
make db-jobs
make db-logs
make db-count
```

---

## Phase 4: Advanced Testing

### Test 6: Multiple Concurrent Jobs
- [ ] Create 3 backup jobs with different schedules
- [ ] Wait for scheduler to execute
- [ ] Verify all jobs executed
- [ ] Check logs for concurrent execution

**Validation:**
```bash
make db-logs
grep -i "starting\|completed" logs/scheduler.log
```

### Test 7: Pre/Post Commands
- [ ] Create job with pre/post commands
- [ ] Execute job
- [ ] Verify commands executed
- [ ] Check logs

**Validation:**
```bash
grep -i "pre-command\|post-command" logs/scheduler.log
```

### Test 8: Exclude Patterns
- [ ] Create job with exclude patterns
- [ ] Execute job
- [ ] Verify excluded files not in backup

**Validation:**
```bash
borg list borgspace/test-backup-1 | grep -E "\.exclude|\.tmp"
```

### Test 9: Large File Handling
- [ ] Add large test file: `make test-file SIZE=500M`
- [ ] Create backup job
- [ ] Execute job
- [ ] Monitor performance

**Validation:**
```bash
make test-file SIZE=500M
make repos-size
grep -i "memory\|duration" logs/scheduler.log
```

### Test 10: Error Handling
- [ ] Create job with invalid source
- [ ] Execute job
- [ ] Verify error handling
- [ ] Check error logs

**Validation:**
```bash
grep -i "error" logs/scheduler.log
sqlite3 config/jogoborg.db "SELECT status, error_message FROM job_logs WHERE status='failed';"
```

---

## Phase 5: Integration Testing

### Test 11: Full Workflow
- [ ] Setup: `./setup.sh`
- [ ] Start: `./run_local.sh`
- [ ] Create job
- [ ] Execute job
- [ ] View logs
- [ ] Check database
- [ ] Stop: `./stop_local.sh`

**Validation:**
- All steps complete without errors

### Test 12: State Reset
- [ ] Create multiple jobs
- [ ] Execute jobs
- [ ] Run `./reset_test_data.sh`
- [ ] Verify clean state
- [ ] Run `./setup.sh` again
- [ ] Verify fresh start

**Validation:**
```bash
make db-count  # Should show 0 jobs
ls -la borgspace/  # Should be empty
```

### Test 13: Service Restart
- [ ] Create job
- [ ] Stop services: `./stop_local.sh`
- [ ] Start services: `./run_local.sh`
- [ ] Verify job still exists
- [ ] Verify data persisted

**Validation:**
```bash
make db-jobs  # Should show job created earlier
```

### Test 14: Configuration Persistence
- [ ] Modify `env.local`
- [ ] Restart services
- [ ] Verify new configuration applied

**Validation:**
- Visual inspection of behavior

### Test 15: Database Consistency
- [ ] Execute multiple jobs
- [ ] Check database integrity: `sqlite3 config/jogoborg.db "PRAGMA integrity_check;"`
- [ ] Verify foreign keys
- [ ] Verify no orphaned records

**Validation:**
```bash
sqlite3 config/jogoborg.db "PRAGMA integrity_check;"
sqlite3 config/jogoborg.db "SELECT COUNT(*) FROM job_logs WHERE job_id NOT IN (SELECT id FROM backup_jobs);"
```

---

## Phase 6: Documentation Review

### README Review
- [ ] Read `local_test/README.md`
- [ ] Verify all instructions accurate
- [ ] Verify all commands work
- [ ] Check troubleshooting section

### Testing Guide Review
- [ ] Read `local_test/TESTING_GUIDE.md`
- [ ] Verify all test scenarios documented
- [ ] Verify all commands work
- [ ] Check troubleshooting section

### Quick Reference Review
- [ ] Read `local_test/QUICK_REFERENCE.md`
- [ ] Verify all commands listed
- [ ] Verify quick start works

### Main Documentation Review
- [ ] Read `LOCAL_TESTING_SETUP.md`
- [ ] Read `TESTING_APPROACH.md`
- [ ] Read `TESTING_SUMMARY.md`
- [ ] Verify all information accurate

---

## Phase 7: Performance Validation

### Performance Test 1: Backup Speed
- [ ] Create 100MB test file: `make test-file SIZE=100M`
- [ ] Create backup job
- [ ] Execute and measure time
- [ ] Verify < 30 seconds

**Validation:**
```bash
grep -i "duration" logs/scheduler.log
```

### Performance Test 2: Memory Usage
- [ ] Create large test file: `make test-file SIZE=500M`
- [ ] Execute backup
- [ ] Check memory usage
- [ ] Verify < 500MB

**Validation:**
```bash
grep -i "max_memory" logs/scheduler.log
```

### Performance Test 3: Concurrent Jobs
- [ ] Create 5 backup jobs
- [ ] Trigger all simultaneously
- [ ] Monitor performance
- [ ] Verify all complete successfully

**Validation:**
```bash
make db-logs
grep -i "duration" logs/scheduler.log
```

---

## Phase 8: Cleanup & Documentation

### Cleanup
- [ ] Remove test files: `make reset`
- [ ] Stop services: `make stop`
- [ ] Verify clean state

### Final Documentation
- [ ] Update README with any findings
- [ ] Document any issues encountered
- [ ] Document any improvements needed
- [ ] Create developer guide

### Git Commit
- [ ] Stage all new files: `git add local_test/`
- [ ] Stage documentation: `git add *.md`
- [ ] Commit with message: `git commit -m "Add local testing environment"`
- [ ] Push to repository: `git push`

---

## Verification Checklist

### All Phases Complete?
- [ ] Phase 1: Files created ✅
- [ ] Phase 2: Validation passed
- [ ] Phase 3: Basic tests passed
- [ ] Phase 4: Advanced tests passed
- [ ] Phase 5: Integration tests passed
- [ ] Phase 6: Documentation reviewed
- [ ] Phase 7: Performance validated
- [ ] Phase 8: Cleanup & documentation complete

### Ready for Production?
- [ ] All tests passing
- [ ] Documentation complete
- [ ] Performance acceptable
- [ ] No known issues
- [ ] Team trained on usage

---

## Quick Validation Commands

Run these to verify everything works:

```bash
# Navigate to local_test
cd local_test

# Check dependencies
make check-deps

# Setup environment
./setup.sh

# Start services
./run_local.sh

# Check status
make status

# Check API
make api-health

# Check database
make db-count

# View logs
make logs

# Stop services
./stop_local.sh

# Reset
./reset_test_data.sh
```

---

## Support & Troubleshooting

### If Setup Fails
1. Check `make check-deps`
2. Install missing dependencies: `make install-deps`
3. Review `local_test/README.md` troubleshooting section
4. Check logs: `tail -f logs/*.log`

### If Tests Fail
1. Check `make status`
2. Review logs: `make logs`
3. Check database: `make db-shell`
4. Review `local_test/TESTING_GUIDE.md` troubleshooting section

### If Performance Issues
1. Check system resources: `top`
2. Check logs for errors: `make logs`
3. Review `local_test/TESTING_GUIDE.md` performance section

---

## Next Steps After Validation

1. **Train team** on local testing environment
2. **Update CI/CD** to use local testing
3. **Add automated tests** to pipeline
4. **Document best practices** for your team
5. **Optimize** based on feedback
6. **Scale** testing as project grows

---

## Success Criteria

✅ **Setup**: Can initialize environment in < 5 minutes
✅ **Startup**: Services start in < 5 seconds
✅ **Testing**: Can create and execute backup job in < 2 minutes
✅ **Debugging**: Can access logs and database directly
✅ **Performance**: Backup operations complete in reasonable time
✅ **Documentation**: All procedures documented and tested
✅ **Team**: Team can use environment without assistance

---

## Timeline

- **Day 1**: Complete Phase 1-2 (Setup & Validation)
- **Day 2**: Complete Phase 3-4 (Basic & Advanced Testing)
- **Day 3**: Complete Phase 5-6 (Integration & Documentation)
- **Day 4**: Complete Phase 7-8 (Performance & Cleanup)

**Total Time: 4 days to full implementation**

---

## Sign-Off

- [ ] All phases complete
- [ ] All tests passing
- [ ] Documentation reviewed
- [ ] Team trained
- [ ] Ready for production use

**Date Completed**: _______________

**Completed By**: _______________

**Notes**: _______________

---

## Appendix: Command Reference

### Setup Commands
```bash
./setup.sh              # Initialize environment
./run_local.sh          # Start services
./stop_local.sh         # Stop services
./reset_test_data.sh    # Reset to clean state
```

### Make Commands
```bash
make setup              # Initialize
make start              # Start services
make stop               # Stop services
make restart            # Restart services
make status             # Show status
make logs               # Follow logs
make db-jobs            # List jobs
make db-logs            # List logs
make repos              # List repositories
make api-health         # Check API
```

### Validation Commands
```bash
make check-deps         # Check dependencies
make install-deps       # Install dependencies
make info               # Show info
make dev-help           # Show helpers
```

### Troubleshooting Commands
```bash
make logs-show-web      # Show web logs
make logs-show-scheduler # Show scheduler logs
make db-shell           # Open database
make db-count           # Show statistics
```

---

**Ready to implement? Start with Phase 1 and work through each phase systematically!** 🚀

