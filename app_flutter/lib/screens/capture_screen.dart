import 'dart:io';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../api_client.dart';
import 'identify_screen.dart';
import 'save_screen.dart';

class CaptureScreen extends StatefulWidget {
  const CaptureScreen({super.key});

  @override
  State<CaptureScreen> createState() => _CaptureScreenState();
}

class _CaptureScreenState extends State<CaptureScreen> {
  final _picker = ImagePicker();
  final _api = ApiClient();
  bool _loading = false;

  Future<void> _pick(ImageSource source) async {
    final xfile = await _picker.pickImage(source: source, maxWidth: 1600, imageQuality: 85);
    if (xfile == null || !mounted) return;
    final photo = File(xfile.path);

    setState(() => _loading = true);
    try {
      final candidates = await _api.identify(photo);
      if (!mounted) return;
      if (candidates.isEmpty) {
        _goToSaveWithoutId(photo);
        return;
      }
      // A successful save further down this flow uses pushAndRemoveUntil to
      // jump straight back to the catalog, clearing this screen along with
      // it — so there's nothing to do with the result here.
      await Navigator.of(context).push<void>(
        MaterialPageRoute(
          builder: (_) => IdentifyScreen(photo: photo, candidates: candidates),
        ),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Identification failed: $e')),
      );
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  void _goToSaveWithoutId(File photo) async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute(builder: (_) => SaveScreen(photo: photo)),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Add a Plant')),
      body: Center(
        child: _loading
            ? const Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  CircularProgressIndicator(),
                  SizedBox(height: 16),
                  Text('Identifying...'),
                ],
              )
            : Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  FilledButton.icon(
                    onPressed: () => _pick(ImageSource.camera),
                    icon: const Icon(Icons.camera_alt),
                    label: const Text('Take a photo'),
                  ),
                  const SizedBox(height: 16),
                  OutlinedButton.icon(
                    onPressed: () => _pick(ImageSource.gallery),
                    icon: const Icon(Icons.photo_library),
                    label: const Text('Choose from gallery'),
                  ),
                ],
              ),
      ),
    );
  }
}
