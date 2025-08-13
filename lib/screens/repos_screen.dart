import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/api_service.dart';
import '../services/auth_service.dart';
import '../widgets/app_drawer.dart';

class ReposScreen extends StatefulWidget {
  const ReposScreen({super.key});

  @override
  State<ReposScreen> createState() => _ReposScreenState();
}

class _ReposScreenState extends State<ReposScreen> {
  List<Map<String, dynamic>> repositories = [];
  bool isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadRepositories();
  }

  Future<void> _loadRepositories() async {
    try {
      final apiService = context.read<ApiService>();
      final authService = context.read<AuthService>();
      
      final response = await apiService.get('/repositories', token: authService.token);
      
      setState(() {
        repositories = List<Map<String, dynamic>>.from(response['repositories'] ?? []);
        isLoading = false;
      });
    } catch (e) {
      setState(() {
        isLoading = false;
      });
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to load repositories: $e')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Borg Repositories'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () {
              setState(() => isLoading = true);
              _loadRepositories();
            },
          ),
        ],
      ),
      drawer: const AppDrawer(),
      body: isLoading
          ? const Center(child: CircularProgressIndicator())
          : repositories.isEmpty
              ? const Center(
                  child: Text(
                    'No repositories found in /borgspace',
                    style: TextStyle(fontSize: 16),
                  ),
                )
              : Padding(
                  padding: const EdgeInsets.all(16),
                  child: GridView.builder(
                    gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                      crossAxisCount: 3,
                      crossAxisSpacing: 16,
                      mainAxisSpacing: 16,
                      childAspectRatio: 1.2,
                    ),
                    itemCount: repositories.length,
                    itemBuilder: (context, index) {
                      final repo = repositories[index];
                      return _RepositoryCard(
                        repository: repo,
                        onTap: () => _showRepositoryDetails(repo),
                      );
                    },
                  ),
                ),
    );
  }

  void _showRepositoryDetails(Map<String, dynamic> repo) {
    showDialog(
      context: context,
      builder: (context) => _RepositoryDialog(repository: repo),
    );
  }
}

class _RepositoryCard extends StatelessWidget {
  final Map<String, dynamic> repository;
  final VoidCallback onTap;

  const _RepositoryCard({
    required this.repository,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 4,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(4),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Icon(Icons.storage, size: 32, color: Colors.blue),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      repository['name'] ?? 'Unknown',
                      style: const TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              Text(
                'Path: ${repository['path']}',
                style: const TextStyle(fontSize: 12, color: Colors.grey),
                overflow: TextOverflow.ellipsis,
              ),
              const SizedBox(height: 4),
              Text(
                'Archives: ${repository['archives_count'] ?? 0}',
                style: const TextStyle(fontSize: 12, color: Colors.grey),
              ),
              if (repository['last_accessed'] != null) ...[
                const SizedBox(height: 4),
                Text(
                  'Last accessed: ${repository['last_accessed']}',
                  style: const TextStyle(fontSize: 10, color: Colors.grey),
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _RepositoryDialog extends StatefulWidget {
  final Map<String, dynamic> repository;

  const _RepositoryDialog({required this.repository});

  @override
  State<_RepositoryDialog> createState() => _RepositoryDialogState();
}

class _RepositoryDialogState extends State<_RepositoryDialog> {
  final _encryptionKeyController = TextEditingController();
  List<Map<String, dynamic>> archives = [];
  bool isLoadingArchives = false;
  bool isUnlocked = false;

  @override
  void dispose() {
    _encryptionKeyController.dispose();
    super.dispose();
  }

  Future<void> _unlockRepository() async {
    if (_encryptionKeyController.text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please enter the encryption key')),
      );
      return;
    }

    setState(() => isLoadingArchives = true);

    try {
      final apiService = context.read<ApiService>();
      final authService = context.read<AuthService>();
      
      final response = await apiService.post(
        '/repositories/${widget.repository['id']}/unlock',
        {'encryption_key': _encryptionKeyController.text},
        token: authService.token,
      );
      
      setState(() {
        archives = List<Map<String, dynamic>>.from(response['archives'] ?? []);
        isUnlocked = true;
        isLoadingArchives = false;
      });
    } catch (e) {
      setState(() => isLoadingArchives = false);
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to unlock repository: $e')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text('Repository: ${widget.repository['name']}'),
      content: SizedBox(
        width: 600,
        height: 500,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Path: ${widget.repository['path']}'),
            const SizedBox(height: 16),
            
            if (!isUnlocked) ...[
              Text(
                'Encryption Key for ${widget.repository['path']}:',
                style: const TextStyle(fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              TextField(
                controller: _encryptionKeyController,
                obscureText: true,
                decoration: InputDecoration(
                  labelText: 'Repository Key - ${widget.repository['path']}',
                  border: const OutlineInputBorder(),
                  suffixIcon: IconButton(
                    icon: const Icon(Icons.lock_open),
                    onPressed: isLoadingArchives ? null : _unlockRepository,
                  ),
                ),
                onSubmitted: (_) => _unlockRepository(),
              ),
              const SizedBox(height: 16),
              
              if (isLoadingArchives)
                const Center(child: CircularProgressIndicator()),
            ] else ...[
              const Text(
                'Archives (newest first):',
                style: TextStyle(fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              
              Expanded(
                child: archives.isEmpty
                    ? const Center(child: Text('No archives found'))
                    : ListView.builder(
                        itemCount: archives.length,
                        itemBuilder: (context, index) {
                          final archive = archives[index];
                          return Card(
                            child: ListTile(
                              leading: const Icon(Icons.archive),
                              title: Text(archive['name'] ?? 'Unknown'),
                              subtitle: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text('Created: ${archive['created_at'] ?? 'Unknown'}'),
                                  if (archive['size'] != null)
                                    Text('Size: ${_formatBytes(archive['size'])}'),
                                  if (archive['files_count'] != null)
                                    Text('Files: ${archive['files_count']}'),
                                ],
                              ),
                              isThreeLine: true,
                            ),
                          );
                        },
                      ),
              ),
            ],
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Close'),
        ),
      ],
    );
  }

  String _formatBytes(int bytes) {
    const suffixes = ['B', 'KB', 'MB', 'GB', 'TB'];
    int i = 0;
    double size = bytes.toDouble();
    
    while (size >= 1024 && i < suffixes.length - 1) {
      size /= 1024;
      i++;
    }
    
    return '${size.toStringAsFixed(1)} ${suffixes[i]}';
  }
}