import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import '../services/auth_service.dart';
import '../services/theme_service.dart';

class JogoborgAppBar extends StatelessWidget implements PreferredSizeWidget {
  final String title;
  final List<Widget>? additionalActions;
  final bool showBackButton;

  const JogoborgAppBar({
    super.key,
    required this.title,
    this.additionalActions,
    this.showBackButton = true,
  });

  @override
  Widget build(BuildContext context) {
    return AppBar(
      title: Text(title),
      leading: showBackButton
          ? IconButton(
              icon: const Icon(Icons.arrow_back),
              tooltip: 'Go Back',
              onPressed: () {
                if (GoRouter.of(context).canPop()) {
                  GoRouter.of(context).pop();
                }
              },
            )
          : null,
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
              tooltip: themeService.isDarkMode
                  ? 'Switch to Light Mode'
                  : 'Switch to Dark Mode',
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
