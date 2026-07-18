import 'package:flutter/material.dart';

import '../api_client.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final _urlController = TextEditingController();
  final _tokenController = TextEditingController();
  final _api = ApiClient();
  String _status = '';
  bool _checking = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    _urlController.text = await ApiClient.getBaseUrl() ?? '';
    _tokenController.text = await ApiClient.getToken() ?? '';
    setState(() {});
  }

  Future<void> _save() async {
    var url = _urlController.text.trim();
    if (url.endsWith('/')) url = url.substring(0, url.length - 1);
    await ApiClient.setBaseUrl(url);
    await ApiClient.setToken(_tokenController.text.trim());
    setState(() => _status = 'Saved.');
  }

  Future<void> _testConnection() async {
    await _save();
    setState(() {
      _checking = true;
      _status = '';
    });
    final ok = await _api.health();
    setState(() {
      _checking = false;
      _status = ok ? 'Connected ✓' : 'Could not reach backend.';
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Settings')),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text('Backend URL', style: TextStyle(fontWeight: FontWeight.bold)),
            const SizedBox(height: 4),
            TextField(
              controller: _urlController,
              decoration: const InputDecoration(
                hintText: 'http://192.168.1.x:8420  or  https://plants.yourdomain.com',
                border: OutlineInputBorder(),
              ),
              keyboardType: TextInputType.url,
            ),
            const SizedBox(height: 16),
            const Text('Bearer token', style: TextStyle(fontWeight: FontWeight.bold)),
            const SizedBox(height: 4),
            TextField(
              controller: _tokenController,
              decoration: const InputDecoration(
                hintText: 'leave blank if API_BEARER_TOKEN is unset on the backend',
                border: OutlineInputBorder(),
              ),
              obscureText: true,
            ),
            const SizedBox(height: 24),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton(onPressed: _save, child: const Text('Save')),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: FilledButton(
                    onPressed: _checking ? null : _testConnection,
                    child: _checking
                        ? const SizedBox(
                            height: 16, width: 16, child: CircularProgressIndicator(strokeWidth: 2))
                        : const Text('Test connection'),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            if (_status.isNotEmpty) Text(_status),
          ],
        ),
      ),
    );
  }
}
