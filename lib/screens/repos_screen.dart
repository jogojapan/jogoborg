import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
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
            tooltip: 'Refresh',
            onPressed: () {
              setState(() => isLoading = true);
              _loadRepositories();
            },
          ),
          IconButton(
            icon: const Icon(Icons.logout),
            onPressed: () async {
              await context.read<AuthService>().logout();
              if (context.mounted) {
                context.go('/login');
              }
            },
          ),
        ],
      ),
      drawer: const AppDrawer(),
      body: isLoading
          ? const Center(child: CircularProgressIndicator())
          : repositories.isEmpty
              ? Center(
                  child: Text(
                    'No repositories found in /borgspace',
                    style: TextStyle(fontSize: 16, color: Colors.grey[400]),
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
    final backgroundColor = Colors.blueGrey[800]; // Slightly lighter than main background for contrast
    final textColor = Colors.grey[300]; // Light gray text
    final mutedTextColor = Colors.grey[400]; // Muted text for details
    
    return Card(
      color: backgroundColor,
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
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                        color: textColor,
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              Text(
                'Path: ${repository['path']}',
                style: TextStyle(fontSize: 12, color: mutedTextColor),
                overflow: TextOverflow.ellipsis,
              ),
              const SizedBox(height: 4),
              Text(
                'Archives: ${repository['archives_count'] ?? 0}',
                style: TextStyle(fontSize: 12, color: mutedTextColor),
              ),
              if (repository['last_accessed'] != null) ...[
                const SizedBox(height: 4),
                Text(
                  'Last accessed: ${repository['last_accessed']}',
                  style: TextStyle(fontSize: 10, color: mutedTextColor),
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
    final backgroundColor = Colors.blueGrey[900]; // Dark gray/blue background
    final textColor = Colors.grey[300]; // Light gray text
    
    return AlertDialog(
      backgroundColor: backgroundColor,
      title: Text('Repository: ${widget.repository['name']}', style: TextStyle(color: textColor)),
      content: SizedBox(
        width: 600,
        height: 500,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Path: ${widget.repository['path']}', style: TextStyle(color: textColor)),
            const SizedBox(height: 16),
            
            if (!isUnlocked) ...[
              Text(
                'Encryption Key for ${widget.repository['path']}:',
                style: TextStyle(fontWeight: FontWeight.bold, color: textColor),
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
              Text(
                'Archives (newest first):',
                style: TextStyle(fontWeight: FontWeight.bold, color: textColor),
              ),
              const SizedBox(height: 8),
              
              Expanded(
                child: archives.isEmpty
                    ? Center(child: Text('No archives found', style: TextStyle(color: textColor)))
                    : ListView.builder(
                        itemCount: archives.length,
                        itemBuilder: (context, index) {
                          final archive = archives[index];
                          return Card(
                            color: Colors.blueGrey[800], // Slightly lighter than dialog background
                            child: ListTile(
                              leading: Icon(Icons.archive, color: Colors.blue[300]),
                              title: Text(archive['name'] ?? 'Unknown', style: TextStyle(color: textColor)),
                              subtitle: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text('Created: ${archive['created_at'] ?? 'Unknown'}', style: TextStyle(color: Colors.grey[400])),
                                  if (archive['size'] != null)
                                    Text('Size: ${_formatBytes(archive['size'])}', style: TextStyle(color: Colors.grey[400])),
                                  if (archive['files_count'] != null)
                                    Text('Files: ${archive['files_count']}', style: TextStyle(color: Colors.grey[400])),
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