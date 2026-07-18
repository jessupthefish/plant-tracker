import 'dart:io';

import 'package:flutter/material.dart';

import '../api_client.dart';
import 'detail_screen.dart';

class SaveScreen extends StatefulWidget {
  final File photo;
  final String? speciesScientific;
  final String? commonName;
  final double? idConfidence;
  final String? idSource;
  final String? variety;

  const SaveScreen({
    super.key,
    required this.photo,
    this.speciesScientific,
    this.commonName,
    this.idConfidence,
    this.idSource,
    this.variety,
  });

  @override
  State<SaveScreen> createState() => _SaveScreenState();
}

class _SaveScreenState extends State<SaveScreen> {
  final _api = ApiClient();
  late final _speciesController = TextEditingController(text: widget.speciesScientific ?? '');
  late final _commonNameController = TextEditingController(text: widget.commonName ?? '');
  late final _varietyController = TextEditingController(text: widget.variety ?? '');
  final _collectionController = TextEditingController();
  final _tagsController = TextEditingController();
  final _priceController = TextEditingController();
  final _notesController = TextEditingController();
  int _quantity = 1;
  bool _forSale = false;
  bool _saving = false;
  List<String> _collectionSuggestions = [];

  @override
  void initState() {
    super.initState();
    _api.listCollections().then((c) {
      if (mounted) setState(() => _collectionSuggestions = c);
    }).catchError((_) {});
  }

  Future<void> _save() async {
    setState(() => _saving = true);
    try {
      final tags = _tagsController.text
          .split(',')
          .map((t) => t.trim())
          .where((t) => t.isNotEmpty)
          .toList();
      final priceText = _priceController.text.trim();
      final plant = await _api.createPlant(
        speciesScientific: _speciesController.text.trim().isEmpty ? null : _speciesController.text.trim(),
        commonName: _commonNameController.text.trim().isEmpty ? null : _commonNameController.text.trim(),
        variety: _varietyController.text.trim().isEmpty ? null : _varietyController.text.trim(),
        collection: _collectionController.text.trim().isEmpty ? null : _collectionController.text.trim(),
        tags: tags,
        quantity: _quantity,
        forSale: _forSale,
        priceCents: priceText.isEmpty ? null : (double.parse(priceText) * 100).round(),
        userNotes: _notesController.text.trim().isEmpty ? null : _notesController.text.trim(),
        idConfidence: widget.idConfidence,
        idSource: widget.idSource,
        photo: widget.photo,
      );
      if (!mounted) return;
      // Drop the whole capture/identify/save stack and land on
      // [Catalog, Detail] so the back button on Detail goes straight to
      // the catalog, not back through the now-irrelevant capture steps.
      await Navigator.of(context).pushAndRemoveUntil(
        MaterialPageRoute(builder: (_) => DetailScreen(plantId: plant.id)),
        (route) => route.isFirst,
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Save failed: $e')));
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Tag & Save')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          ClipRRect(
            borderRadius: BorderRadius.circular(12),
            child: Image.file(widget.photo, height: 160, fit: BoxFit.cover, width: double.infinity),
          ),
          const SizedBox(height: 16),
          TextField(
            controller: _speciesController,
            decoration: const InputDecoration(labelText: 'Species (scientific name)', border: OutlineInputBorder()),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _commonNameController,
            decoration: const InputDecoration(labelText: 'Common name', border: OutlineInputBorder()),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _varietyController,
            decoration: const InputDecoration(labelText: 'Variety / cultivar', border: OutlineInputBorder()),
          ),
          const SizedBox(height: 12),
          Autocomplete<String>(
            optionsBuilder: (value) => value.text.isEmpty
                ? _collectionSuggestions
                : _collectionSuggestions.where(
                    (c) => c.toLowerCase().contains(value.text.toLowerCase())),
            onSelected: (value) => _collectionController.text = value,
            fieldViewBuilder: (context, controller, focusNode, onSubmit) {
              controller.addListener(() => _collectionController.text = controller.text);
              return TextField(
                controller: controller,
                focusNode: focusNode,
                decoration: const InputDecoration(labelText: 'Collection', border: OutlineInputBorder()),
              );
            },
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _tagsController,
            decoration: const InputDecoration(
              labelText: 'Tags (comma separated)',
              border: OutlineInputBorder(),
              hintText: 'aroid, climbing, rare',
            ),
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              const Text('Quantity'),
              const Spacer(),
              IconButton(
                onPressed: _quantity > 1 ? () => setState(() => _quantity--) : null,
                icon: const Icon(Icons.remove_circle_outline),
              ),
              Text('$_quantity', style: const TextStyle(fontSize: 16)),
              IconButton(
                onPressed: () => setState(() => _quantity++),
                icon: const Icon(Icons.add_circle_outline),
              ),
            ],
          ),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('For sale'),
            value: _forSale,
            onChanged: (v) => setState(() => _forSale = v),
          ),
          if (_forSale)
            TextField(
              controller: _priceController,
              decoration: const InputDecoration(labelText: 'Price (USD)', border: OutlineInputBorder()),
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
            ),
          const SizedBox(height: 12),
          TextField(
            controller: _notesController,
            decoration: const InputDecoration(labelText: 'Notes', border: OutlineInputBorder()),
            maxLines: 3,
          ),
          const SizedBox(height: 24),
          FilledButton(
            onPressed: _saving ? null : _save,
            child: _saving
                ? const SizedBox(height: 16, width: 16, child: CircularProgressIndicator(strokeWidth: 2))
                : const Text('Save plant'),
          ),
        ],
      ),
    );
  }
}
