import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'services/auth_service.dart';
import 'services/api_service.dart';
import 'services/theme_service.dart';
import 'screens/login_screen.dart';
import 'screens/dashboard_screen.dart';
import 'screens/repos_screen.dart';
import 'screens/sources_screen.dart';
import 'screens/jobs_screen.dart';
import 'screens/notifications_screen.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  final authService = AuthService();

  try {
    await authService.initialize();
  } catch (e) {
    debugPrint('Error initializing AuthService: $e');
  }

  runApp(JogoborgApp(authService: authService));
}

class JogoborgApp extends StatelessWidget {
  final AuthService authService;

  const JogoborgApp({super.key, required this.authService});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider<AuthService>.value(value: authService),
        ChangeNotifierProvider(create: (_) => ApiService()),
        ChangeNotifierProvider(create: (_) => ThemeService()),
      ],
      child: Consumer<AuthService>(
        builder: (context, authService, _) {
          return Consumer<ThemeService>(
            builder: (context, themeService, _) {
              return MaterialApp.router(
                title: 'Jogoborg - Borg Backup Manager',
                theme: ThemeService.lightTheme,
                darkTheme: ThemeService.darkTheme,
                themeMode: themeService.themeMode,
                routerConfig: _createRouter(authService),
              );
            },
          );
        },
      ),
    );
  }

  GoRouter _createRouter(AuthService authService) {
    return GoRouter(
      initialLocation: '/login',
      refreshListenable: authService,
      redirect: (context, state) {
        final isAuthenticated = authService.isAuthenticated;
        final isLoginRoute = state.matchedLocation == '/login';

        if (!isAuthenticated && !isLoginRoute) {
          return '/login';
        }
        if (isAuthenticated && isLoginRoute) {
          return '/dashboard';
        }
        return null;
      },
      routes: [
        GoRoute(
          path: '/login',
          builder: (context, state) => const LoginScreen(),
        ),
        GoRoute(
          path: '/dashboard',
          builder: (context, state) => const DashboardScreen(),
        ),
        GoRoute(
          path: '/repos',
          builder: (context, state) => const ReposScreen(),
        ),
        GoRoute(
          path: '/sources',
          builder: (context, state) => const SourcesScreen(),
        ),
        GoRoute(
          path: '/jobs',
          builder: (context, state) => const JobsScreen(),
        ),
        GoRoute(
          path: '/notifications',
          builder: (context, state) => const NotificationsScreen(),
        ),
      ],
    );
  }
}
