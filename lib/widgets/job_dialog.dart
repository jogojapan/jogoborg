import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/api_service.dart';
import '../services/auth_service.dart';

class JobDialog extends StatefulWidget {
  final Map<String, dynamic>? job;

  const JobDialog({super.key, this.job});

  @override
  State<JobDialog> createState() => _JobDialogState();
}

class _JobDialogState extends State<JobDialog> {
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();
  final _scheduleController = TextEditingController();
  final _compressionController = TextEditingController();
  final _excludePatternsController = TextEditingController();
  final _keepDailyController = TextEditingController();
  final _keepMonthlyController = TextEditingController();
  final _keepYearlyController = TextEditingController();
  final _preCommandController = TextEditingController();
  final _postCommandController = TextEditingController();
  final _repositoryPassphraseController = TextEditingController();
  
  List<String> sourceDirs = [];
  Map<String, dynamic>? s3Config;
  Map<String, dynamic>? dbConfig;
  
  bool isEditing = false;
  bool isSaving = false;

  @override
  void initState() {
    super.initState();
    isEditing = widget.job != null;
    _loadJobData();
  }

  void _loadJobData() {
    if (widget.job != null) {
      final job = widget.job!;
      _nameController.text = job['name'] ?? '';
      _scheduleController.text = job['schedule'] ?? '';
      _compressionController.text = job['compression'] ?? 'lz4';
      _excludePatternsController.text = job['exclude_patterns'] ?? '';
      _keepDailyController.text = (job['keep_daily'] ?? 7).toString();
      _keepMonthlyController.text = (job['keep_monthly'] ?? 6).toString();
      _keepYearlyController.text = (job['keep_yearly'] ?? 1).toString();
      _preCommandController.text = job['pre_command'] ?? '';
      _postCommandController.text = job['post_command'] ?? '';
      _repositoryPassphraseController.text = job['repository_passphrase'] ?? '';
      
      if (job['source_directories'] is List) {
        sourceDirs = List<String>.from(job['source_directories']);
      } else if (job['source_directories'] is String) {
        sourceDirs = (job['source_directories'] as String).split(',');
      }
      
      if (job['s3_config'] is Map) {
        s3Config = Map<String, dynamic>.from(job['s3_config']);
      }
      
      if (job['db_config'] is Map) {
        dbConfig = Map<String, dynamic>.from(job['db_config']);
      }
    } else {
      _compressionController.text = 'lz4';
      _keepDailyController.text = '7';
      _keepMonthlyController.text = '6';
      _keepYearlyController.text = '1';
    }
  }

  @override
  void dispose() {
    _nameController.dispose();
    _scheduleController.dispose();
    _compressionController.dispose();
    _excludePatternsController.dispose();
    _keepDailyController.dispose();
    _keepMonthlyController.dispose();
    _keepYearlyController.dispose();
    _preCommandController.dispose();
    _postCommandController.dispose();
    _repositoryPassphraseController.dispose();
    super.dispose();
  }

  Future<void> _saveJob() async {
    if (!_formKey.currentState!.validate()) return;
    
    if (sourceDirs.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please add at least one source directory')),
      );
      return;
    }
    
    if (_repositoryPassphraseController.text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Repository passphrase is required')),
      );
      return;
    }

    setState(() => isSaving = true);

    try {
      final apiService = context.read<ApiService>();
      final authService = context.read<AuthService>();
      
      final jobData = {
        'name': _nameController.text,
        'schedule': _scheduleController.text,
        'compression': _compressionController.text,
        'exclude_patterns': _excludePatternsController.text,
        'keep_daily': int.tryParse(_keepDailyController.text) ?? 7,
        'keep_monthly': int.tryParse(_keepMonthlyController.text) ?? 6,
        'keep_yearly': int.tryParse(_keepYearlyController.text) ?? 1,
        'source_directories': sourceDirs,
        'pre_command': _preCommandController.text,
        'post_command': _postCommandController.text,
        'repository_passphrase': _repositoryPassphraseController.text,
        's3_config': s3Config,
        'db_config': dbConfig,
      };
      
      if (isEditing) {
        await apiService.put(
          '/jobs/${widget.job!['id']}',
          jobData,
          token: authService.token,
        );
      } else {
        await apiService.post('/jobs', jobData, token: authService.token);
      }
      
      if (mounted) {
        Navigator.of(context).pop(true);
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to save job: $e')),
        );
      }
    } finally {
      if (mounted) {
        setState(() => isSaving = false);
      }
    }
  }

  void _addSourceDirectory() async {
    final result = await showDialog<String>(
      context: context,
      builder: (context) => const _DirectoryPickerDialog(),
    );
    
    if (result != null && !sourceDirs.contains(result)) {
      setState(() {
        sourceDirs.add(result);
      });
    }
  }

  void _removeSourceDirectory(String dir) {
    setState(() {
      sourceDirs.remove(dir);
    });
  }

  void _configureS3() async {
    final result = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (context) => _S3ConfigDialog(initialConfig: s3Config),
    );
    
    if (result != null) {
      setState(() {
        s3Config = result;
      });
    }
  }

  void _configureCommands() async {
    final result = await showDialog<Map<String, String>>(
      context: context,
      builder: (context) => _CommandsConfigDialog(
        preCommand: _preCommandController.text,
        postCommand: _postCommandController.text,
      ),
    );
    
    if (result != null) {
      setState(() {
        _preCommandController.text = result['preCommand'] ?? '';
        _postCommandController.text = result['postCommand'] ?? '';
      });
    }
  }

  void _configureDatabase() async {
    final result = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (context) => _DatabaseConfigDialog(initialConfig: dbConfig),
    );
    
    if (result != null) {
      setState(() {
        dbConfig = result;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      child: Container(
        width: 800,
        height: 700,
        padding: const EdgeInsets.all(24),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                isEditing ? 'Edit Backup Job' : 'New Backup Job',
                style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 24),
              
              Expanded(
                child: ListView(
                  children: [
                    // Basic settings
                    Row(
                      children: [
                        Expanded(
                          child: TextFormField(
                            controller: _nameController,
                            decoration: const InputDecoration(
                              labelText: 'Job Name',
                              border: OutlineInputBorder(),
                            ),
                            validator: (value) {
                              if (value == null || value.isEmpty) {
                                return 'Please enter a job name';
                              }
                              return null;
                            },
                          ),
                        ),
                        const SizedBox(width: 16),
                        Expanded(
                          child: TextFormField(
                            controller: _scheduleController,
                            decoration: const InputDecoration(
                              labelText: 'Schedule (cron)',
                              hintText: '0 2 * * *',
                              border: OutlineInputBorder(),
                            ),
                            validator: (value) {
                              if (value == null || value.isEmpty) {
                                return 'Please enter a schedule';
                              }
                              return null;
                            },
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 16),
                    
                    // Repository passphrase
                    TextFormField(
                      controller: _repositoryPassphraseController,
                      decoration: const InputDecoration(
                        labelText: 'Repository Passphrase',
                        hintText: 'Enter a strong passphrase for Borg encryption',
                        border: OutlineInputBorder(),
                        helperText: 'This passphrase encrypts your backups. Keep it safe!',
                      ),
                      obscureText: true,
                      autocorrect: false,
                      enableSuggestions: false,
                      keyboardType: TextInputType.visiblePassword,
                      textInputAction: TextInputAction.next,
                      autofillHints: const [AutofillHints.newPassword],
                      validator: (value) {
                        if (value == null || value.isEmpty) {
                          return 'Repository passphrase is required';
                        }
                        if (value.length < 8) {
                          return 'Passphrase must be at least 8 characters';
                        }
                        return null;
                      },
                    ),
                    const SizedBox(height: 16),
                    
                    // Action buttons
                    Row(
                      children: [
                        ElevatedButton.icon(
                          onPressed: _configureS3,
                          icon: const Icon(Icons.cloud),
                          label: Text(s3Config != null ? 'S3 Configured' : 'Configure S3'),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: s3Config != null ? Colors.green : null,
                          ),
                        ),
                        const SizedBox(width: 8),
                        ElevatedButton.icon(
                          onPressed: _configureCommands,
                          icon: const Icon(Icons.terminal),
                          label: Text((_preCommandController.text.isNotEmpty || _postCommandController.text.isNotEmpty) ? 'Commands Configured' : 'Configure Commands'),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: (_preCommandController.text.isNotEmpty || _postCommandController.text.isNotEmpty) ? Colors.green : null,
                          ),
                        ),
                        const SizedBox(width: 8),
                        ElevatedButton.icon(
                          onPressed: _configureDatabase,
                          icon: const Icon(Icons.storage),
                          label: Text(dbConfig != null ? 'DB Configured' : 'Configure DB'),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: dbConfig != null ? Colors.green : null,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 16),
                    
                    // Compression and exclusions
                    TextFormField(
                      controller: _compressionController,
                      decoration: const InputDecoration(
                        labelText: 'Compression',
                        hintText: 'lz4',
                        border: OutlineInputBorder(),
                      ),
                    ),
                    const SizedBox(height: 16),
                    
                    TextFormField(
                      controller: _excludePatternsController,
                      decoration: const InputDecoration(
                        labelText: 'Exclude Patterns (one per line)',
                        hintText: '*.log\n*.tmp',
                        border: OutlineInputBorder(),
                      ),
                      maxLines: 3,
                    ),
                    const SizedBox(height: 16),
                    
                    // Retention settings
                    Row(
                      children: [
                        Expanded(
                          child: TextFormField(
                            controller: _keepDailyController,
                            decoration: const InputDecoration(
                              labelText: 'Keep Daily',
                              border: OutlineInputBorder(),
                            ),
                            keyboardType: TextInputType.number,
                          ),
                        ),
                        const SizedBox(width: 16),
                        Expanded(
                          child: TextFormField(
                            controller: _keepMonthlyController,
                            decoration: const InputDecoration(
                              labelText: 'Keep Monthly',
                              border: OutlineInputBorder(),
                            ),
                            keyboardType: TextInputType.number,
                          ),
                        ),
                        const SizedBox(width: 16),
                        Expanded(
                          child: TextFormField(
                            controller: _keepYearlyController,
                            decoration: const InputDecoration(
                              labelText: 'Keep Yearly',
                              border: OutlineInputBorder(),
                            ),
                            keyboardType: TextInputType.number,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 16),
                    
                    // Source directories
                    const Text(
                      'Source Directories',
                      style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 8),
                    
                    ElevatedButton.icon(
                      onPressed: _addSourceDirectory,
                      icon: const Icon(Icons.add),
                      label: const Text('Add Source Directory'),
                    ),
                    const SizedBox(height: 8),
                    
                    ...sourceDirs.map((dir) => Card(
                      child: ListTile(
                        leading: const Icon(Icons.folder),
                        title: Text(dir),
                        trailing: IconButton(
                          icon: const Icon(Icons.remove),
                          onPressed: () => _removeSourceDirectory(dir),
                        ),
                      ),
                    )),
                  ],
                ),
              ),
              
              // Action buttons
              const SizedBox(height: 16),
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  TextButton(
                    onPressed: () => Navigator.of(context).pop(),
                    child: const Text('Cancel'),
                  ),
                  const SizedBox(width: 8),
                  ElevatedButton(
                    onPressed: isSaving ? null : _saveJob,
                    child: isSaving
                        ? const CircularProgressIndicator()
                        : Text(isEditing ? 'Save' : 'Create'),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _DirectoryPickerDialog extends StatefulWidget {
  const _DirectoryPickerDialog();

  @override
  State<_DirectoryPickerDialog> createState() => _DirectoryPickerDialogState();
}

class _DirectoryPickerDialogState extends State<_DirectoryPickerDialog> {
  String currentPath = '/sourcespace';
  List<Map<String, dynamic>> items = [];
  bool isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadDirectory();
  }

  Future<void> _loadDirectory() async {
    setState(() => isLoading = true);

    try {
      final apiService = context.read<ApiService>();
      final authService = context.read<AuthService>();
      
      final response = await apiService.post(
        '/sources/browse',
        {'path': currentPath},
        token: authService.token,
      );
      
      setState(() {
        items = List<Map<String, dynamic>>.from(response['items'] ?? []);
        isLoading = false;
      });
    } catch (e) {
      setState(() => isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Select Source Directory'),
      content: SizedBox(
        width: 500,
        height: 400,
        child: Column(
          children: [
            // Current path and navigation
            Row(
              children: [
                Expanded(
                  child: Text(
                    currentPath,
                    style: const TextStyle(fontWeight: FontWeight.bold),
                  ),
                ),
                ElevatedButton(
                  onPressed: () => Navigator.of(context).pop(currentPath),
                  child: const Text('Select This Directory'),
                ),
              ],
            ),
            const Divider(),
            
            // Directory contents
            Expanded(
              child: isLoading
                  ? const Center(child: CircularProgressIndicator())
                  : ListView.builder(
                      itemCount: items.length,
                      itemBuilder: (context, index) {
                        final item = items[index];
                        final isDirectory = item['is_directory'] == true;
                        
                        if (!isDirectory) return const SizedBox.shrink();
                        
                        return ListTile(
                          leading: const Icon(Icons.folder, color: Colors.blue),
                          title: Text(item['name'] ?? 'Unknown'),
                          onTap: () {
                            setState(() {
                              currentPath = item['path'];
                            });
                            _loadDirectory();
                          },
                        );
                      },
                    ),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Cancel'),
        ),
      ],
    );
  }
}

class _S3ConfigDialog extends StatefulWidget {
  final Map<String, dynamic>? initialConfig;

  const _S3ConfigDialog({this.initialConfig});

  @override
  State<_S3ConfigDialog> createState() => _S3ConfigDialogState();
}

class _S3ConfigDialogState extends State<_S3ConfigDialog> {
  final _endpointController = TextEditingController();
  final _bucketController = TextEditingController();
  final _regionController = TextEditingController();
  final _accessKeyController = TextEditingController();
  final _secretKeyController = TextEditingController();
  String _storageClass = 'STANDARD';
  String _provider = 'aws';

  @override
  void initState() {
    super.initState();
    if (widget.initialConfig != null) {
      final config = widget.initialConfig!;
      _endpointController.text = config['endpoint'] ?? '';
      _bucketController.text = config['bucket'] ?? '';
      _regionController.text = config['region'] ?? 'us-east-1';
      _accessKeyController.text = config['access_key'] ?? '';
      _secretKeyController.text = config['secret_key'] ?? '';
      _storageClass = config['storage_class'] ?? 'STANDARD';
      _provider = config['provider'] ?? 'aws';
    } else {
      _regionController.text = 'us-east-1';
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('S3 Configuration'),
      content: SizedBox(
        width: 400,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            DropdownButtonFormField<String>(
              value: _provider,
              decoration: const InputDecoration(
                labelText: 'Provider',
                border: OutlineInputBorder(),
              ),
              items: const [
                DropdownMenuItem(value: 'aws', child: Text('Amazon S3')),
                DropdownMenuItem(value: 'minio', child: Text('MinIO')),
              ],
              onChanged: (value) => setState(() => _provider = value!),
            ),
            const SizedBox(height: 16),
            
            if (_provider == 'minio')
              TextFormField(
                controller: _endpointController,
                decoration: const InputDecoration(
                  labelText: 'Endpoint',
                  hintText: 'https://minio.example.com',
                  border: OutlineInputBorder(),
                ),
              ),
            if (_provider == 'minio') const SizedBox(height: 16),
            
            TextFormField(
              controller: _bucketController,
              decoration: const InputDecoration(
                labelText: 'Bucket Name',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 16),
            
            if (_provider == 'aws')
              TextFormField(
                controller: _regionController,
                decoration: const InputDecoration(
                  labelText: 'AWS Region',
                  hintText: 'e.g., us-east-1, eu-north-1',
                  border: OutlineInputBorder(),
                ),
              ),
            if (_provider == 'aws') const SizedBox(height: 16),
            
            TextFormField(
              controller: _accessKeyController,
              decoration: const InputDecoration(
                labelText: 'Access Key',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 16),
            
            TextFormField(
              controller: _secretKeyController,
              decoration: const InputDecoration(
                labelText: 'Secret Key',
                border: OutlineInputBorder(),
              ),
              obscureText: true,
            ),
            const SizedBox(height: 16),
            
            if (_provider == 'aws')
              DropdownButtonFormField<String>(
                value: _storageClass,
                decoration: const InputDecoration(
                  labelText: 'Storage Class',
                  border: OutlineInputBorder(),
                ),
                items: const [
                  DropdownMenuItem(value: 'STANDARD', child: Text('Standard')),
                  DropdownMenuItem(value: 'STANDARD_IA', child: Text('Standard-IA')),
                  DropdownMenuItem(value: 'GLACIER', child: Text('Glacier')),
                  DropdownMenuItem(value: 'DEEP_ARCHIVE', child: Text('Deep Archive')),
                ],
                onChanged: (value) => setState(() => _storageClass = value!),
              ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Cancel'),
        ),
        ElevatedButton(
          onPressed: () {
            final config = {
              'provider': _provider,
              'endpoint': _endpointController.text,
              'bucket': _bucketController.text,
              'region': _regionController.text,
              'access_key': _accessKeyController.text,
              'secret_key': _secretKeyController.text,
              'storage_class': _storageClass,
            };
            Navigator.of(context).pop(config);
          },
          child: const Text('Save'),
        ),
      ],
    );
  }
}

class _DatabaseConfigDialog extends StatefulWidget {
  final Map<String, dynamic>? initialConfig;

  const _DatabaseConfigDialog({this.initialConfig});

  @override
  State<_DatabaseConfigDialog> createState() => _DatabaseConfigDialogState();
}

class _CommandsConfigDialog extends StatefulWidget {
  final String preCommand;
  final String postCommand;

  const _CommandsConfigDialog({
    required this.preCommand,
    required this.postCommand,
  });

  @override
  State<_CommandsConfigDialog> createState() => _CommandsConfigDialogState();
}

class _CommandsConfigDialogState extends State<_CommandsConfigDialog> {
  final _preCommandController = TextEditingController();
  final _postCommandController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _preCommandController.text = widget.preCommand;
    _postCommandController.text = widget.postCommand;
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Configure Commands'),
      content: SizedBox(
        width: 500,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Configure commands to run before and after backup execution. Use these to suspend/resume services during backups.',
              style: TextStyle(color: Colors.grey, fontSize: 14),
            ),
            const SizedBox(height: 16),
            
            TextFormField(
              controller: _preCommandController,
              decoration: const InputDecoration(
                labelText: 'Pre-Command (runs before backup)',
                hintText: 'docker stop myservice',
                border: OutlineInputBorder(),
                helperText: 'Command to run before the backup starts (e.g., suspend services)',
              ),
              maxLines: 2,
            ),
            const SizedBox(height: 16),
            
            TextFormField(
              controller: _postCommandController,
              decoration: const InputDecoration(
                labelText: 'Post-Command (runs after backup)',
                hintText: 'docker start myservice',
                border: OutlineInputBorder(),
                helperText: 'Command to run after backup completes (success or failure)',
              ),
              maxLines: 2,
            ),
            const SizedBox(height: 16),
            
            const Text(
              'Note: Commands will run with a 5-minute timeout. Non-zero exit codes will be logged as warnings but won\'t fail the backup.',
              style: TextStyle(color: Colors.orange, fontSize: 12),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Cancel'),
        ),
        ElevatedButton(
          onPressed: () {
            final result = {
              'preCommand': _preCommandController.text,
              'postCommand': _postCommandController.text,
            };
            Navigator.of(context).pop(result);
          },
          child: const Text('Save'),
        ),
      ],
    );
  }
}

class _DatabaseConfigDialogState extends State<_DatabaseConfigDialog> {
  final _hostController = TextEditingController();
  final _portController = TextEditingController();
  final _usernameController = TextEditingController();
  final _passwordController = TextEditingController();
  final _databaseController = TextEditingController();
  final _tablesController = TextEditingController();
  String _dbType = 'postgresql';

  @override
  void initState() {
    super.initState();
    if (widget.initialConfig != null) {
      final config = widget.initialConfig!;
      _hostController.text = config['host'] ?? '';
      _portController.text = (config['port'] ?? 5432).toString();
      _usernameController.text = config['username'] ?? '';
      _passwordController.text = config['password'] ?? '';
      _databaseController.text = config['database'] ?? '';
      _tablesController.text = (config['tables'] as List?)?.join('\n') ?? '';
      _dbType = config['type'] ?? 'postgresql';
    } else {
      _portController.text = '5432';
    }
  }

  Future<void> _testConnection() async {
    try {
      final apiService = context.read<ApiService>();
      final authService = context.read<AuthService>();
      
      await apiService.post(
        '/database/test',
        {
          'type': _dbType,
          'host': _hostController.text,
          'port': int.tryParse(_portController.text) ?? 5432,
          'username': _usernameController.text,
          'password': _passwordController.text,
          'database': _databaseController.text,
          'tables': _tablesController.text.split('\n'),
        },
        token: authService.token,
      );
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Database connection successful!'),
            backgroundColor: Colors.green,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Connection failed: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Database Configuration'),
      content: SizedBox(
        width: 400,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            DropdownButtonFormField<String>(
              value: _dbType,
              decoration: const InputDecoration(
                labelText: 'Database Type',
                border: OutlineInputBorder(),
              ),
              items: const [
                DropdownMenuItem(value: 'postgresql', child: Text('PostgreSQL')),
                DropdownMenuItem(value: 'mariadb', child: Text('MariaDB/MySQL')),
              ],
              onChanged: (value) {
                setState(() {
                  _dbType = value!;
                  _portController.text = value == 'postgresql' ? '5432' : '3306';
                });
              },
            ),
            const SizedBox(height: 16),
            
            Row(
              children: [
                Expanded(
                  flex: 3,
                  child: TextFormField(
                    controller: _hostController,
                    decoration: const InputDecoration(
                      labelText: 'Host',
                      border: OutlineInputBorder(),
                    ),
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  flex: 1,
                  child: TextFormField(
                    controller: _portController,
                    decoration: const InputDecoration(
                      labelText: 'Port',
                      border: OutlineInputBorder(),
                    ),
                    keyboardType: TextInputType.number,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            
            TextFormField(
              controller: _usernameController,
              decoration: const InputDecoration(
                labelText: 'Username',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 16),
            
            TextFormField(
              controller: _passwordController,
              decoration: const InputDecoration(
                labelText: 'Password',
                border: OutlineInputBorder(),
              ),
              obscureText: true,
            ),
            const SizedBox(height: 16),
            
            TextFormField(
              controller: _databaseController,
              decoration: const InputDecoration(
                labelText: 'Database Name',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 16),
            
            TextFormField(
              controller: _tablesController,
              decoration: const InputDecoration(
                labelText: 'Tables (one per line)',
                hintText: 'users\norders\nproducts',
                border: OutlineInputBorder(),
              ),
              maxLines: 3,
            ),
            const SizedBox(height: 16),
            
            ElevatedButton(
              onPressed: _testConnection,
              child: const Text('Test Connection'),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Cancel'),
        ),
        ElevatedButton(
          onPressed: () {
            final config = {
              'type': _dbType,
              'host': _hostController.text,
              'port': int.tryParse(_portController.text) ?? 5432,
              'username': _usernameController.text,
              'password': _passwordController.text,
              'database': _databaseController.text,
              'tables': _tablesController.text.split('\n').where((t) => t.isNotEmpty).toList(),
            };
            Navigator.of(context).pop(config);
          },
          child: const Text('Save'),
        ),
      ],
    );
  }
}