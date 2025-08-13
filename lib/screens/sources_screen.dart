import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';
import '../services/api_service.dart';
import '../services/auth_service.dart';
import '../widgets/app_drawer.dart';

class SourcesScreen extends StatefulWidget {
  const SourcesScreen({super.key});

  @override
  State<SourcesScreen> createState() => _SourcesScreenState();
}

class _SourcesScreenState extends State<SourcesScreen> {
  String currentPath = '/sourcespace';
  List<Map<String, dynamic>> items = [];
  bool isLoading = true;
  List<String> pathHistory = ['/sourcespace'];

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
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to load directory: $e')),
        );
      }
    }
  }

  void _navigateToPath(String path) {
    setState(() {
      currentPath = path;
      if (pathHistory.isEmpty || pathHistory.last != path) {
        pathHistory.add(path);
      }
    });
    _loadDirectory();
  }

  void _goBack() {
    if (pathHistory.length > 1) {
      pathHistory.removeLast();
      setState(() {
        currentPath = pathHistory.last;
      });
      _loadDirectory();
    }
  }

  void _goUp() {
    if (currentPath != '/sourcespace' && currentPath != '/') {
      final parentPath = currentPath.substring(0, currentPath.lastIndexOf('/'));
      final newPath = parentPath.isEmpty ? '/' : parentPath;
      _navigateToPath(newPath);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Source Directories'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadDirectory,
          ),
        ],
      ),
      drawer: const AppDrawer(),
      body: Column(
        children: [
          // Navigation bar
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.grey[100],
              border: Border(bottom: BorderSide(color: Colors.grey[300]!)),
            ),
            child: Row(
              children: [
                IconButton(
                  icon: const Icon(Icons.arrow_back),
                  onPressed: pathHistory.length > 1 ? _goBack : null,
                ),
                IconButton(
                  icon: const Icon(Icons.arrow_upward),
                  onPressed: currentPath != '/sourcespace' ? _goUp : null,
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Text(
                    currentPath,
                    style: const TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ],
            ),
          ),
          
          // Directory contents
          Expanded(
            child: isLoading
                ? const Center(child: CircularProgressIndicator())
                : items.isEmpty
                    ? const Center(
                        child: Text(
                          'Directory is empty',
                          style: TextStyle(fontSize: 16),
                        ),
                      )
                    : ListView.builder(
                        itemCount: items.length,
                        itemBuilder: (context, index) {
                          final item = items[index];
                          return _FileListTile(
                            item: item,
                            onTap: () {
                              if (item['is_directory'] == true) {
                                _navigateToPath(item['path']);
                              }
                            },
                          );
                        },
                      ),
          ),
        ],
      ),
    );
  }
}

class _FileListTile extends StatefulWidget {
  final Map<String, dynamic> item;
  final VoidCallback? onTap;

  const _FileListTile({
    required this.item,
    this.onTap,
  });

  @override
  State<_FileListTile> createState() => _FileListTileState();
}

class _FileListTileState extends State<_FileListTile> {
  bool showingSize = false;
  String? calculatedSize;

  Future<void> _calculateSize() async {
    if (showingSize) return;
    
    setState(() => showingSize = true);
    
    try {
      final apiService = context.read<ApiService>();
      final authService = context.read<AuthService>();
      
      final response = await apiService.post(
        '/sources/size',
        {'path': widget.item['path']},
        token: authService.token,
      );
      
      setState(() {
        calculatedSize = _formatBytes(response['size'] ?? 0);
      });
    } catch (e) {
      setState(() {
        calculatedSize = 'Error';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDirectory = widget.item['is_directory'] == true;
    final size = widget.item['size'];
    final lastModified = widget.item['last_modified'];
    final permissions = widget.item['permissions'];

    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
      child: ListTile(
        leading: Icon(
          isDirectory ? Icons.folder : Icons.insert_drive_file,
          color: isDirectory ? Colors.blue : Colors.grey[600],
          size: 32,
        ),
        title: Text(
          widget.item['name'] ?? 'Unknown',
          style: TextStyle(
            fontWeight: isDirectory ? FontWeight.bold : FontWeight.normal,
          ),
        ),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (permissions != null)
              Text(
                'Permissions: $permissions',
                style: const TextStyle(fontSize: 12),
              ),
            Row(
              children: [
                if (isDirectory) ...[
                  Text(
                    calculatedSize != null 
                        ? 'Size: $calculatedSize'
                        : showingSize 
                            ? 'Calculating...'
                            : 'Size: Click to calculate',
                    style: const TextStyle(fontSize: 12),
                  ),
                  if (!showingSize && calculatedSize == null) ...[
                    const SizedBox(width: 8),
                    InkWell(
                      onTap: _calculateSize,
                      child: const Icon(Icons.calculate, size: 16),
                    ),
                  ],
                ] else if (size != null) ...[
                  Text(
                    'Size: ${_formatBytes(size)}',
                    style: const TextStyle(fontSize: 12),
                  ),
                ],
                const Spacer(),
                if (lastModified != null)
                  Text(
                    DateFormat('yyyy-MM-dd HH:mm').format(
                      DateTime.parse(lastModified),
                    ),
                    style: const TextStyle(fontSize: 12),
                  ),
              ],
            ),
          ],
        ),
        onTap: widget.onTap,
        trailing: isDirectory ? const Icon(Icons.chevron_right) : null,
      ),
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