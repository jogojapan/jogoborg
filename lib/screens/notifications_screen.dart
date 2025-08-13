import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/api_service.dart';
import '../services/auth_service.dart';
import '../widgets/app_drawer.dart';
import '../widgets/jogoborg_app_bar.dart';

class NotificationsScreen extends StatefulWidget {
  const NotificationsScreen({super.key});

  @override
  State<NotificationsScreen> createState() => _NotificationsScreenState();
}

class _NotificationsScreenState extends State<NotificationsScreen> {
  final _formKey = GlobalKey<FormState>();
  
  // SMTP settings
  final _smtpHostController = TextEditingController();
  final _smtpPortController = TextEditingController();
  final _smtpUsernameController = TextEditingController();
  final _smtpPasswordController = TextEditingController();
  final _smtpSenderEmailController = TextEditingController();
  final _smtpRecipientEmailController = TextEditingController();
  String _smtpSecurity = 'STARTTLS';
  
  // Webhook settings
  final _webhookUrlController = TextEditingController();
  final _webhookTokenController = TextEditingController();
  String _successPriority = 'normal';
  String _errorPriority = 'high';
  
  bool isLoading = true;
  bool isSaving = false;

  @override
  void initState() {
    super.initState();
    _loadSettings();
  }

  @override
  void dispose() {
    _smtpHostController.dispose();
    _smtpPortController.dispose();
    _smtpUsernameController.dispose();
    _smtpPasswordController.dispose();
    _smtpSenderEmailController.dispose();
    _smtpRecipientEmailController.dispose();
    _webhookUrlController.dispose();
    _webhookTokenController.dispose();
    super.dispose();
  }

  Future<void> _loadSettings() async {
    setState(() => isLoading = true);

    try {
      final apiService = context.read<ApiService>();
      final authService = context.read<AuthService>();
      
      final response = await apiService.get('/notifications/edit', token: authService.token);
      final settings = response['settings'] ?? {};
      
      // Load SMTP settings
      final smtpConfig = settings['smtp_config'] ?? {};
      _smtpHostController.text = smtpConfig['host'] ?? '';
      _smtpPortController.text = (smtpConfig['port'] ?? '587').toString();
      _smtpUsernameController.text = smtpConfig['username'] ?? '';
      _smtpPasswordController.text = smtpConfig['password'] ?? '';
      _smtpSenderEmailController.text = smtpConfig['sender_email'] ?? '';
      _smtpRecipientEmailController.text = smtpConfig['recipient_email'] ?? '';
      _smtpSecurity = smtpConfig['security'] ?? 'STARTTLS';
      
      // Load webhook settings
      final webhookConfig = settings['webhook_config'] ?? {};
      _webhookUrlController.text = webhookConfig['url'] ?? '';
      _webhookTokenController.text = webhookConfig['token'] ?? '';
      _successPriority = webhookConfig['success_priority'] ?? 'normal';
      _errorPriority = webhookConfig['error_priority'] ?? 'high';
      
      setState(() => isLoading = false);
    } catch (e) {
      setState(() => isLoading = false);
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to load notification settings: $e')),
        );
      }
    }
  }

  Future<void> _saveSettings() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() => isSaving = true);

    try {
      final apiService = context.read<ApiService>();
      final authService = context.read<AuthService>();
      
      final settings = {
        'smtp_config': {
          'host': _smtpHostController.text,
          'port': int.tryParse(_smtpPortController.text) ?? 587,
          'username': _smtpUsernameController.text,
          'password': _smtpPasswordController.text,
          'sender_email': _smtpSenderEmailController.text,
          'recipient_email': _smtpRecipientEmailController.text,
          'security': _smtpSecurity,
        },
        'webhook_config': {
          'url': _webhookUrlController.text,
          'token': _webhookTokenController.text,
          'success_priority': _successPriority,
          'error_priority': _errorPriority,
        },
      };
      
      await apiService.put('/notifications', settings, token: authService.token);
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Notification settings saved successfully')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to save settings: $e')),
        );
      }
    } finally {
      if (mounted) {
        setState(() => isSaving = false);
      }
    }
  }

  Future<void> _testSmtp() async {
    try {
      final apiService = context.read<ApiService>();
      final authService = context.read<AuthService>();
      
      await apiService.post(
        '/notifications/test/smtp',
        {
          'host': _smtpHostController.text,
          'port': int.tryParse(_smtpPortController.text) ?? 587,
          'username': _smtpUsernameController.text,
          'password': _smtpPasswordController.text,
          'sender_email': _smtpSenderEmailController.text,
          'recipient_email': _smtpRecipientEmailController.text,
          'security': _smtpSecurity,
        },
        token: authService.token,
      );
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('SMTP test successful!'),
            backgroundColor: Colors.green,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('SMTP test failed: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  Future<void> _testWebhook() async {
    try {
      final apiService = context.read<ApiService>();
      final authService = context.read<AuthService>();
      
      await apiService.post(
        '/notifications/test/webhook',
        {
          'url': _webhookUrlController.text,
          'token': _webhookTokenController.text,
          'priority': 'normal',
        },
        token: authService.token,
      );
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Webhook test successful!'),
            backgroundColor: Colors.green,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Webhook test failed: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: JogoborgAppBar(
        title: 'Notification Settings',
        additionalActions: [
          IconButton(
            icon: const Icon(Icons.save),
            tooltip: 'Save Settings',
            onPressed: isSaving ? null : _saveSettings,
          ),
        ],
      ),
      drawer: const AppDrawer(),
      body: isLoading
          ? const Center(child: CircularProgressIndicator())
          : Form(
              key: _formKey,
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  // SMTP Configuration
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              const Icon(Icons.email, color: Colors.blue),
                              const SizedBox(width: 8),
                              const Text(
                                'SMTP Configuration',
                                style: TextStyle(
                                  fontSize: 20,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                              const Spacer(),
                              ElevatedButton(
                                onPressed: _testSmtp,
                                child: const Text('Test'),
                              ),
                            ],
                          ),
                          const SizedBox(height: 16),
                          
                          TextFormField(
                            controller: _smtpHostController,
                            decoration: const InputDecoration(
                              labelText: 'SMTP Host',
                              hintText: 'smtp.gmail.com',
                              border: OutlineInputBorder(),
                            ),
                          ),
                          const SizedBox(height: 16),
                          
                          Row(
                            children: [
                              Expanded(
                                flex: 2,
                                child: TextFormField(
                                  controller: _smtpPortController,
                                  decoration: const InputDecoration(
                                    labelText: 'Port',
                                    hintText: '587 (STARTTLS) / 465 (SSL)',
                                    border: OutlineInputBorder(),
                                    helperText: '587=STARTTLS, 465=SSL, 25=None',
                                  ),
                                  keyboardType: TextInputType.number,
                                ),
                              ),
                              const SizedBox(width: 16),
                              Expanded(
                                flex: 3,
                                child: DropdownButtonFormField<String>(
                                  value: _smtpSecurity,
                                  decoration: const InputDecoration(
                                    labelText: 'Security',
                                    border: OutlineInputBorder(),
                                  ),
                                  items: const [
                                    DropdownMenuItem(value: 'STARTTLS', child: Text('STARTTLS')),
                                    DropdownMenuItem(value: 'SSL', child: Text('SSL/TLS')),
                                    DropdownMenuItem(value: 'NONE', child: Text('None')),
                                  ],
                                  onChanged: (value) {
                                    setState(() {
                                      _smtpSecurity = value!;
                                      // Auto-update port based on security type if port is default
                                      if (_smtpPortController.text == '587' || _smtpPortController.text == '465' || _smtpPortController.text.isEmpty) {
                                        if (value == 'SSL') {
                                          _smtpPortController.text = '465';
                                        } else if (value == 'STARTTLS') {
                                          _smtpPortController.text = '587';
                                        } else {
                                          _smtpPortController.text = '25';
                                        }
                                      }
                                    });
                                  },
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 16),
                          
                          TextFormField(
                            controller: _smtpUsernameController,
                            decoration: const InputDecoration(
                              labelText: 'Username',
                              border: OutlineInputBorder(),
                            ),
                          ),
                          const SizedBox(height: 16),
                          
                          TextFormField(
                            controller: _smtpPasswordController,
                            decoration: const InputDecoration(
                              labelText: 'Password',
                              border: OutlineInputBorder(),
                            ),
                            obscureText: true,
                          ),
                          const SizedBox(height: 16),
                          
                          TextFormField(
                            controller: _smtpSenderEmailController,
                            decoration: const InputDecoration(
                              labelText: 'Sender Email Address',
                              hintText: 'backups@example.com',
                              border: OutlineInputBorder(),
                            ),
                            validator: (value) {
                              if (value == null || value.isEmpty) {
                                return 'Sender email address is required';
                              }
                              if (!RegExp(r'^[\w-\.]+@([\w-]+\.)+[\w-]{2,4}$').hasMatch(value)) {
                                return 'Enter a valid email address';
                              }
                              return null;
                            },
                          ),
                          const SizedBox(height: 16),
                          
                          TextFormField(
                            controller: _smtpRecipientEmailController,
                            decoration: const InputDecoration(
                              labelText: 'Recipient Email Address (optional)',
                              hintText: 'admin@example.com',
                              border: OutlineInputBorder(),
                              helperText: 'Leave empty to send to sender address',
                            ),
                            validator: (value) {
                              if (value != null && value.isNotEmpty) {
                                if (!RegExp(r'^[\w-\.]+@([\w-]+\.)+[\w-]{2,4}$').hasMatch(value)) {
                                  return 'Enter a valid email address';
                                }
                              }
                              return null;
                            },
                          ),
                        ],
                      ),
                    ),
                  ),
                  
                  const SizedBox(height: 24),
                  
                  // Webhook Configuration
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              const Icon(Icons.webhook, color: Colors.green),
                              const SizedBox(width: 8),
                              const Text(
                                'Webhook Configuration (Gotify)',
                                style: TextStyle(
                                  fontSize: 20,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                              const Spacer(),
                              ElevatedButton(
                                onPressed: _testWebhook,
                                child: const Text('Test'),
                              ),
                            ],
                          ),
                          const SizedBox(height: 16),
                          
                          TextFormField(
                            controller: _webhookUrlController,
                            decoration: const InputDecoration(
                              labelText: 'Gotify Server URL',
                              hintText: 'https://notify.chobycat.com',
                              border: OutlineInputBorder(),
                              helperText: 'Base URL only - /message will be added automatically',
                            ),
                          ),
                          const SizedBox(height: 16),
                          
                          TextFormField(
                            controller: _webhookTokenController,
                            decoration: const InputDecoration(
                              labelText: 'App Token',
                              border: OutlineInputBorder(),
                            ),
                          ),
                          const SizedBox(height: 16),
                          
                          Row(
                            children: [
                              Expanded(
                                child: DropdownButtonFormField<String>(
                                  value: _successPriority,
                                  decoration: const InputDecoration(
                                    labelText: 'Success Priority',
                                    border: OutlineInputBorder(),
                                  ),
                                  items: const [
                                    DropdownMenuItem(value: 'low', child: Text('Low')),
                                    DropdownMenuItem(value: 'normal', child: Text('Normal')),
                                    DropdownMenuItem(value: 'high', child: Text('High')),
                                  ],
                                  onChanged: (value) {
                                    setState(() => _successPriority = value!);
                                  },
                                ),
                              ),
                              const SizedBox(width: 16),
                              Expanded(
                                child: DropdownButtonFormField<String>(
                                  value: _errorPriority,
                                  decoration: const InputDecoration(
                                    labelText: 'Error Priority',
                                    border: OutlineInputBorder(),
                                  ),
                                  items: const [
                                    DropdownMenuItem(value: 'low', child: Text('Low')),
                                    DropdownMenuItem(value: 'normal', child: Text('Normal')),
                                    DropdownMenuItem(value: 'high', child: Text('High')),
                                  ],
                                  onChanged: (value) {
                                    setState(() => _errorPriority = value!);
                                  },
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ),
                  
                  const SizedBox(height: 24),
                  
                  // Save button
                  SizedBox(
                    width: double.infinity,
                    height: 48,
                    child: ElevatedButton(
                      onPressed: isSaving ? null : _saveSettings,
                      child: isSaving
                          ? const CircularProgressIndicator()
                          : const Text('Save Settings'),
                    ),
                  ),
                ],
              ),
            ),
    );
  }
}