import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import '../services/auth_service.dart';
import '../services/color_config.dart';

class AppDrawer extends StatelessWidget {
  const AppDrawer({super.key});

  @override
  Widget build(BuildContext context) {
    final currentLocation = GoRouterState.of(context).matchedLocation;
    final backgroundColor = AppColors.drawerBackground;
    final textColor = AppColors.primaryText;

    return Drawer(
      backgroundColor: backgroundColor,
      child: Column(
        children: [
          const DrawerHeader(
            decoration: BoxDecoration(color: Colors.blue),
            child: SizedBox(
              width: double.infinity,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    'Jogoborg',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 24,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  SizedBox(height: 8),
                  Text(
                    'Borg Backup Manager',
                    style: TextStyle(
                      color: Colors.white70,
                      fontSize: 16,
                    ),
                  ),
                ],
              ),
            ),
          ),
          Expanded(
            child: ListView(
              padding: EdgeInsets.zero,
              children: [
                _DrawerItem(
                  icon: Icons.dashboard,
                  title: 'Dashboard',
                  selected: currentLocation == '/dashboard',
                  onTap: () => context.go('/dashboard'),
                ),
                _DrawerItem(
                  icon: Icons.storage,
                  title: 'Repositories',
                  selected: currentLocation == '/repos',
                  onTap: () => context.go('/repos'),
                ),
                _DrawerItem(
                  icon: Icons.folder,
                  title: 'Source Directories',
                  selected: currentLocation == '/sources',
                  onTap: () => context.go('/sources'),
                ),
                _DrawerItem(
                  icon: Icons.backup,
                  title: 'Backup Jobs',
                  selected: currentLocation == '/jobs',
                  onTap: () => context.go('/jobs'),
                ),
                _DrawerItem(
                  icon: Icons.notifications,
                  title: 'Notifications',
                  selected: currentLocation == '/notifications',
                  onTap: () => context.go('/notifications'),
                ),
              ],
            ),
          ),
          const Divider(),
          ListTile(
            leading: Icon(Icons.logout, color: textColor),
            title: Text('Logout', style: TextStyle(color: textColor)),
            onTap: () async {
              await context.read<AuthService>().logout();
              if (context.mounted) {
                context.go('/login');
              }
            },
          ),
          const SizedBox(height: 16),
        ],
      ),
    );
  }
}

class _DrawerItem extends StatelessWidget {
  final IconData icon;
  final String title;
  final bool selected;
  final VoidCallback onTap;

  const _DrawerItem({
    required this.icon,
    required this.title,
    required this.selected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final textColor = AppColors.primaryText;
    final selectedColor = AppColors.selectedBlue;
    
    return ListTile(
      leading: Icon(
        icon,
        color: selected ? selectedColor : textColor,
      ),
      title: Text(
        title,
        style: TextStyle(
          color: selected ? selectedColor : textColor,
          fontWeight: selected ? FontWeight.bold : null,
        ),
      ),
      selected: selected,
      onTap: onTap,
    );
  }
}