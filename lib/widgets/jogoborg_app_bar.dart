import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import '../services/auth_service.dart';
import '../services/theme_service.dart';

class JogoborgAppBar extends StatelessWidget implements PreferredSizeWidget {
  final String title;
  final List<Widget>? additionalActions;

  const JogoborgAppBar({
    super.key,
    required this.title,
    this.additionalActions,
  });

  @override
  Widget build(BuildContext context) {
    return AppBar(
      title: Text(title),
      actions: [
        // Additional actions provided by the screen
        if (additionalActions != null) ...additionalActions!,
        
        // Theme toggle button
        Consumer<ThemeService>(
          builder: (context, themeService, child) {
            return IconButton(
              icon: Icon(
                themeService.isDarkMode ? Icons.light_mode : Icons.dark_mode,
              ),
              tooltip: themeService.isDarkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode',
              onPressed: () {
                themeService.toggleTheme();
              },
            );
          },
        ),
        
        // Logout button
        IconButton(
          icon: const Icon(Icons.logout),
          tooltip: 'Logout',
          onPressed: () async {
            await context.read<AuthService>().logout();
            if (context.mounted) {
              context.go('/login');
            }
          },
        ),
      ],
    );
  }

  @override
  Size get preferredSize => const Size.fromHeight(kToolbarHeight);
}