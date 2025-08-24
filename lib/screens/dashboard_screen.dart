import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import '../services/auth_service.dart';
import '../services/color_config.dart';
import '../widgets/app_drawer.dart';

class DashboardScreen extends StatelessWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Jogoborg Dashboard'),
        actions: [
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
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: GridView.count(
          crossAxisCount: 2,
          crossAxisSpacing: 16,
          mainAxisSpacing: 16,
          children: [
            _DashboardCard(
              title: 'Borg Repositories',
              subtitle: 'View and manage backup repositories',
              icon: Icons.storage,
              color: Colors.blue,
              onTap: () => context.go('/repos'),
            ),
            _DashboardCard(
              title: 'Source Directories',
              subtitle: 'Browse source file tree',
              icon: Icons.folder,
              color: Colors.green,
              onTap: () => context.go('/sources'),
            ),
            _DashboardCard(
              title: 'Backup Jobs',
              subtitle: 'Configure and monitor backup jobs',
              icon: Icons.backup,
              color: Colors.orange,
              onTap: () => context.go('/jobs'),
            ),
            _DashboardCard(
              title: 'Notifications',
              subtitle: 'Setup SMTP and webhook notifications',
              icon: Icons.notifications,
              color: Colors.purple,
              onTap: () => context.go('/notifications'),
            ),
          ],
        ),
      ),
    );
  }
}

class _DashboardCard extends StatelessWidget {
  final String title;
  final String subtitle;
  final IconData icon;
  final Color color;
  final VoidCallback onTap;

  const _DashboardCard({
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.color,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final backgroundColor = AppColors.cardBackground;
    final textColor = AppColors.primaryText;
    
    return Card(
      color: backgroundColor,
      elevation: 4,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(4),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(icon, size: 48, color: color),
              const SizedBox(height: 16),
              Text(
                title,
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                  color: textColor,
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 8),
              Text(
                subtitle,
                style: TextStyle(
                  fontSize: 14,
                  color: AppColors.secondaryText,
                ),
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      ),
    );
  }
}