import 'dart:math';

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../services/color_config.dart';
import '../widgets/app_drawer.dart';
import '../widgets/jogoborg_app_bar.dart';

class DashboardScreen extends StatelessWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: const JogoborgAppBar(
        title: 'Jogoborg Dashboard',
        showBackButton: false,
      ),
      drawer: const AppDrawer(),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: GridView.count(
          crossAxisCount: _calculateCrossAxisCount(context),
          crossAxisSpacing: 16,
          mainAxisSpacing: 16,
          children: [
            _DashboardCard(
              title: 'Borg Repositories',
              subtitle: 'View and manage backup repositories',
              icon: Icons.storage,
              color: Colors.blue,
              onTap: () => context.push('/repos'),
            ),
            _DashboardCard(
              title: 'Source Directories',
              subtitle: 'Browse source file tree',
              icon: Icons.folder,
              color: Colors.green,
              onTap: () => context.push('/sources'),
            ),
            _DashboardCard(
              title: 'Backup Jobs',
              subtitle: 'Configure and monitor backup jobs',
              icon: Icons.backup,
              color: Colors.orange,
              onTap: () => context.push('/jobs'),
            ),
            _DashboardCard(
              title: 'Notifications',
              subtitle: 'Setup SMTP and webhook notifications',
              icon: Icons.notifications,
              color: Colors.purple,
              onTap: () => context.push('/notifications'),
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

int _calculateCrossAxisCount(BuildContext context) {
  final screenWidth = MediaQuery.of(context).size.width;
  // Minimum card width in logical pixels
  const minCardWidth = 240.0;
  // Padding and spacing
  const horizontalPadding = 16.0 * 2; // left and right padding
  const spacing = 16.0;

  final availableWidth = screenWidth - horizontalPadding;
  // Calculate how many cards fit
  final count = max(1, (availableWidth / (minCardWidth + spacing)).floor());
  return count;
}
