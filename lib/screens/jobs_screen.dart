import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';
import '../services/api_service.dart';
import '../services/auth_service.dart';
import '../services/color_config.dart';
import '../widgets/app_drawer.dart';
import '../widgets/job_dialog.dart';
import '../widgets/jogoborg_app_bar.dart';

class JobsScreen extends StatefulWidget {
  const JobsScreen({super.key});

  @override
  State<JobsScreen> createState() => _JobsScreenState();
}

class _JobsScreenState extends State<JobsScreen> {
  List<Map<String, dynamic>> jobs = [];
  bool isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadJobs();
  }

  Future<void> _loadJobs() async {
    setState(() => isLoading = true);

    try {
      final apiService = context.read<ApiService>();
      final authService = context.read<AuthService>();

      final response = await apiService.get('/jobs', token: authService.token);

      if (mounted) {
        setState(() {
          jobs = List<Map<String, dynamic>>.from(response['jobs'] ?? []);
          isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() => isLoading = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to load jobs: $e')),
        );
      }
    }
  }

  Future<void> _createJob() async {
    final result = await showDialog<bool>(
      context: context,
      builder: (context) => const JobDialog(),
    );

    if (result == true) {
      _loadJobs(); // Refresh the job list
    }
  }

  Future<void> _editJob(Map<String, dynamic> job) async {
    final result = await showDialog<bool>(
      context: context,
      builder: (context) => JobDialog(job: job),
    );

    if (result == true) {
      _loadJobs(); // Refresh the job list
    }
  }

  Future<void> _deleteJob(Map<String, dynamic> job) async {
    // Extract context-dependent values before any async operation
    final apiService = context.read<ApiService>();
    final authService = context.read<AuthService>();
    final messenger = ScaffoldMessenger.of(context);

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Job'),
        content: Text('Are you sure you want to delete job "${job['name']}"?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.of(context).pop(true),
            style: TextButton.styleFrom(foregroundColor: Colors.red),
            child: const Text('Delete'),
          ),
        ],
      ),
    );

    if (confirmed != true) return;

    try {
      await apiService.delete('/jobs/${job['id']}', token: authService.token);

      if (mounted) {
        messenger.showSnackBar(
          const SnackBar(content: Text('Job deleted successfully')),
        );
        _loadJobs();
      }
    } catch (e) {
      if (mounted) {
        messenger.showSnackBar(
          SnackBar(content: Text('Failed to delete job: $e')),
        );
      }
    }
  }

  Future<void> _triggerJob(Map<String, dynamic> job) async {
    // Extract context-dependent values before any async operation
    final apiService = context.read<ApiService>();
    final authService = context.read<AuthService>();
    final messenger = ScaffoldMessenger.of(context);

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Run Job Now'),
        content: Text(
            'Are you sure you want to trigger job "${job['name']}" right now?\n\nThis will start the backup process immediately.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.of(context).pop(true),
            style: TextButton.styleFrom(foregroundColor: Colors.green),
            child: const Text('Run Now'),
          ),
        ],
      ),
    );

    if (confirmed != true) return;

    try {
      await apiService.post('/jobs/${job['id']}/trigger', {},
          token: authService.token);

      if (mounted) {
        messenger.showSnackBar(
          SnackBar(
              content: Text(
                  'Job "${job['name']}" has been triggered and is running in the background')),
        );
        _loadJobs(); // Refresh the job list to show updated status
      }
    } catch (e) {
      if (mounted) {
        messenger.showSnackBar(
          SnackBar(content: Text('Failed to trigger job: $e')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: JogoborgAppBar(
        title: 'Backup Jobs',
        additionalActions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Refresh',
            onPressed: _loadJobs,
          ),
        ],
      ),
      drawer: const AppDrawer(),
      floatingActionButton: FloatingActionButton(
        onPressed: _createJob,
        child: const Icon(Icons.add),
      ),
      body: isLoading
          ? const Center(child: CircularProgressIndicator())
          : jobs.isEmpty
              ? const Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.backup, size: 64, color: Colors.grey),
                      SizedBox(height: 16),
                      Text(
                        'No backup jobs configured',
                        style: TextStyle(fontSize: 18, color: Colors.grey),
                      ),
                      SizedBox(height: 8),
                      Text(
                        'Tap the + button to create your first backup job',
                        style: TextStyle(fontSize: 14, color: Colors.grey),
                      ),
                    ],
                  ),
                )
              : Padding(
                  padding: const EdgeInsets.all(16),
                  child: ListView.builder(
                    itemCount: jobs.length,
                    itemBuilder: (context, index) {
                      final job = jobs[index];
                      return _JobCard(
                        key: ValueKey(job['id']),
                        job: job,
                        onEdit: () => _editJob(job),
                        onDelete: () => _deleteJob(job),
                        onTrigger: () => _triggerJob(job),
                      );
                    },
                  ),
                ),
    );
  }
}

class _JobCard extends StatelessWidget {
  final Map<String, dynamic> job;
  final VoidCallback onEdit;
  final VoidCallback onDelete;
  final VoidCallback onTrigger;

  const _JobCard({
    super.key,
    required this.job,
    required this.onEdit,
    required this.onDelete,
    required this.onTrigger,
  });

  @override
  Widget build(BuildContext context) {
    final sourceDirs = job['source_directories'] is String
        ? (job['source_directories'] as String).split(',')
        : List<String>.from(job['source_directories'] ?? []);

    // Use centralized color configuration
    final backgroundColor = AppColors.cardBackground;
    final textColor = AppColors.primaryText;
    final mutedTextColor = AppColors.secondaryText;

    return Card(
      color: backgroundColor, // Set the background color of the card
      margin: const EdgeInsets.only(bottom: 16),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        job['name'] ?? 'Unnamed Job',
                        style: TextStyle(
                          fontSize: 20,
                          fontWeight: FontWeight.bold,
                          color: textColor,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        'Schedule: ${job['schedule'] ?? 'Not set'}',
                        style: TextStyle(
                          fontSize: 14,
                          color: mutedTextColor, // Set muted text color
                        ),
                      ),
                    ],
                  ),
                ),
                PopupMenuButton<String>(
                  onSelected: (value) {
                    switch (value) {
                      case 'trigger':
                        onTrigger();
                        break;
                      case 'edit':
                        onEdit();
                        break;
                      case 'delete':
                        onDelete();
                        break;
                    }
                  },
                  itemBuilder: (context) => [
                    PopupMenuItem(
                      value: 'trigger',
                      child: Row(
                        children: [
                          Icon(Icons.play_arrow, color: Colors.green),
                          SizedBox(width: 8),
                          const Text('Run Now'),
                        ],
                      ),
                    ),
                    PopupMenuItem(
                      value: 'edit',
                      child: Row(
                        children: [
                          Icon(Icons.edit),
                          SizedBox(width: 8),
                          Text('Edit', style: TextStyle(color: textColor)),
                        ],
                      ),
                    ),
                    PopupMenuItem(
                      value: 'delete',
                      child: Row(
                        children: [
                          Icon(Icons.delete, color: Colors.red),
                          SizedBox(width: 8),
                          Text('Delete', style: TextStyle(color: textColor)),
                        ],
                      ),
                    ),
                  ],
                ),
              ],
            ),
            const SizedBox(height: 12),
            // Job details
            _JobDetailRow(
              label: 'Compression',
              value: job['compression'] ?? 'lz4',
              textColor: textColor,
            ),
            _JobDetailRow(
              label: 'Retention',
              value:
                  'Daily: ${job['keep_daily']}, Monthly: ${job['keep_monthly']}, Yearly: ${job['keep_yearly']}',
              textColor: textColor,
            ),
            if (sourceDirs.isNotEmpty) ...[
              const SizedBox(height: 8),
              Text(
                'Source Directories:',
                style: TextStyle(fontWeight: FontWeight.bold, color: textColor),
              ),
              const SizedBox(height: 4),
              ...sourceDirs.map((dir) => Padding(
                    padding: const EdgeInsets.only(left: 16, bottom: 2),
                    child: Row(
                      children: [
                        Icon(Icons.folder, size: 16, color: Colors.blue),
                        SizedBox(width: 8),
                        Expanded(
                            child:
                                Text(dir, style: TextStyle(color: textColor))),
                      ],
                    ),
                  )),
            ],
            // Last run logs
            const SizedBox(height: 12),
            _LastRunsSection(jobId: job['id']),
            // Action buttons
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: onTrigger,
                    icon: Icon(Icons.play_arrow),
                    label: Text('Run Now'),
                    style: ElevatedButton.styleFrom(
                      foregroundColor: Colors.white,
                      backgroundColor: Colors.green,
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: ElevatedButton(
                    onPressed: onEdit,
                    child: Text('Details'),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _JobDetailRow extends StatelessWidget {
  final String label;
  final String value;
  final Color? textColor;

  const _JobDetailRow({
    required this.label,
    required this.value,
    this.textColor,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 100,
            child: Text(
              '$label:',
              style: TextStyle(fontWeight: FontWeight.bold, color: textColor),
            ),
          ),
          Expanded(child: Text(value, style: TextStyle(color: textColor))),
        ],
      ),
    );
  }
}

class _LastRunsSection extends StatefulWidget {
  final int jobId;

  const _LastRunsSection({required this.jobId});

  @override
  State<_LastRunsSection> createState() => _LastRunsSectionState();
}

class _LastRunsSectionState extends State<_LastRunsSection> {
  List<Map<String, dynamic>> lastRuns = [];
  bool isLoading = false;

  @override
  void initState() {
    super.initState();
    _loadLastRuns();
  }

  Future<void> _loadLastRuns() async {
    setState(() => isLoading = true);

    try {
      final apiService = context.read<ApiService>();
      final authService = context.read<AuthService>();

      final response = await apiService.get(
        '/jobs/${widget.jobId}/logs?limit=3',
        token: authService.token,
      );

      setState(() {
        lastRuns = List<Map<String, dynamic>>.from(response['logs'] ?? []);
        isLoading = false;
      });
    } catch (e) {
      setState(() => isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (isLoading) {
      return const Center(
        child: Padding(
          padding: EdgeInsets.all(8.0),
          child: CircularProgressIndicator(),
        ),
      );
    }

    if (lastRuns.isEmpty) {
      return Text(
        'Last runs: No runs yet',
        style: TextStyle(color: AppColors.secondaryText),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Last 3 runs:',
          style: TextStyle(
              fontWeight: FontWeight.bold, color: AppColors.primaryText),
        ),
        const SizedBox(height: 4),
        ...lastRuns.map((run) {
          final status = run['status'] ?? 'unknown';
          final startedAt = run['started_at'] != null
              ? DateTime.parse(run['started_at'])
              : null;
          final finishedAt = run['finished_at'] != null
              ? DateTime.parse(run['finished_at'])
              : null;

          final statusColor = status == 'completed'
              ? Colors.green
              : status == 'failed'
                  ? Colors.red
                  : Colors.orange;

          return Padding(
            padding: const EdgeInsets.only(left: 16, bottom: 2),
            child: Row(
              children: [
                Icon(
                  status == 'completed'
                      ? Icons.check_circle
                      : status == 'failed'
                          ? Icons.error
                          : Icons.schedule,
                  size: 16,
                  color: statusColor,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    startedAt != null
                        ? '${DateFormat('MMM dd, HH:mm').format(startedAt)} - ${status.toUpperCase()}'
                        : 'Unknown time - ${status.toUpperCase()}',
                    style: TextStyle(
                      fontSize: 12,
                      color: statusColor,
                    ),
                  ),
                ),
                if (finishedAt != null && startedAt != null)
                  Text(
                    '(${finishedAt.difference(startedAt).inMinutes}m)',
                    style: const TextStyle(fontSize: 12, color: Colors.grey),
                  ),
              ],
            ),
          );
        }),
      ],
    );
  }
}
