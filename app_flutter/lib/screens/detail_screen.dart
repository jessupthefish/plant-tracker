import 'dart:io';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../api_client.dart';
import '../models/plant.dart';
import '../widgets/authenticated_image.dart';

class DetailScreen extends StatefulWidget {
  final String plantId;

  const DetailScreen({super.key, required this.plantId});

  @override
  State<DetailScreen> createState() => _DetailScreenState();
}

class _DetailScreenState extends State<DetailScreen> {
  final _api = ApiClient();
  final _picker = ImagePicker();
  Plant? _plant;
  bool _editing = false;
  bool _busy = false;

  final _pageController = PageController();
  int _photoIndex = 0;

  final _speciesController = TextEditingController();
  final _commonNameController = TextEditingController();
  final _varietyController = TextEditingController();
  final _collectionController = TextEditingController();
  final _tagsController = TextEditingController();
  final _quantityController = TextEditingController();
  final _priceController = TextEditingController();
  final _notesController = TextEditingController();
  final _careLightController = TextEditingController();
  final _careWaterController = TextEditingController();
  final _careSoilController = TextEditingController();
  final _careTemperatureController = TextEditingController();
  final _careHumidityController = TextEditingController();
  final _careFertilizerController = TextEditingController();
  bool _forSale = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final plant = await _api.getPlant(widget.plantId);
    if (!mounted) return;
    setState(() {
      _plant = plant;
      _speciesController.text = plant.speciesScientific ?? '';
      _commonNameController.text = plant.commonName ?? '';
      _varietyController.text = plant.variety ?? '';
      _collectionController.text = plant.collection ?? '';
      _tagsController.text = plant.tags.join(', ');
      _quantityController.text = plant.quantity.toString();
      _priceController.text = plant.priceCents != null ? (plant.priceCents! / 100).toStringAsFixed(2) : '';
      _notesController.text = plant.userNotes ?? '';
      _careLightController.text = plant.careLight ?? '';
      _careWaterController.text = plant.careWater ?? '';
      _careSoilController.text = plant.careSoil ?? '';
      _careTemperatureController.text = plant.careTemperature ?? '';
      _careHumidityController.text = plant.careHumidity ?? '';
      _careFertilizerController.text = plant.careFertilizer ?? '';
      _forSale = plant.forSale;
      _photoIndex = _photoIndex.clamp(0, (plant.photos.length - 1).clamp(0, 1 << 30));
    });
  }

  Future<void> _save() async {
    setState(() => _busy = true);
    try {
      final priceText = _priceController.text.trim();
      final updated = await _api.updatePlant(widget.plantId, {
        'species_scientific': _speciesController.text.trim(),
        'common_name': _commonNameController.text.trim(),
        'variety': _varietyController.text.trim(),
        'collection': _collectionController.text.trim(),
        'tags': _tagsController.text.split(',').map((t) => t.trim()).where((t) => t.isNotEmpty).toList(),
        'quantity': int.tryParse(_quantityController.text.trim()) ?? _plant!.quantity,
        'for_sale': _forSale,
        'price_cents': priceText.isEmpty ? null : (double.parse(priceText) * 100).round(),
        'user_notes': _notesController.text.trim(),
        'care_light': _careLightController.text.trim(),
        'care_water': _careWaterController.text.trim(),
        'care_soil': _careSoilController.text.trim(),
        'care_temperature': _careTemperatureController.text.trim(),
        'care_humidity': _careHumidityController.text.trim(),
        'care_fertilizer': _careFertilizerController.text.trim(),
      });
      if (!mounted) return;
      setState(() {
        _plant = updated;
        _editing = false;
      });
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Update failed: $e')));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _regenerateCare() async {
    setState(() => _busy = true);
    try {
      final updated = await _api.regenerateCare(widget.plantId);
      if (!mounted) return;
      setState(() {
        _plant = updated;
        _careLightController.text = updated.careLight ?? '';
        _careWaterController.text = updated.careWater ?? '';
        _careSoilController.text = updated.careSoil ?? '';
        _careTemperatureController.text = updated.careTemperature ?? '';
        _careHumidityController.text = updated.careHumidity ?? '';
        _careFertilizerController.text = updated.careFertilizer ?? '';
      });
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Care regeneration failed: $e')));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _reidentify() async {
    final plant = _plant;
    if (plant == null || plant.photos.isEmpty) return;
    setState(() => _busy = true);
    try {
      final photoId = plant.photos[_photoIndex.clamp(0, plant.photos.length - 1)].id;
      final bytes = await _api.fetchPhotoBytes(plant.id, photoId);
      final tempFile = File('${Directory.systemTemp.path}/reid_${plant.id}_$photoId.jpg');
      await tempFile.writeAsBytes(bytes);

      final candidates = await _api.identify(tempFile);
      if (!mounted) return;
      if (candidates.isEmpty) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('No candidates found for this photo.')),
        );
        return;
      }
      final chosen = await showModalBottomSheet<IdentifyCandidate>(
        context: context,
        builder: (ctx) => ListView(
          shrinkWrap: true,
          children: [
            const Padding(
              padding: EdgeInsets.all(16),
              child: Text('Pick the correct species', style: TextStyle(fontWeight: FontWeight.bold)),
            ),
            for (final c in candidates)
              ListTile(
                title: Text(c.scientificName, style: const TextStyle(fontStyle: FontStyle.italic)),
                subtitle: Text(c.commonNames.isNotEmpty ? c.commonNames.join(', ') : 'No common name'),
                trailing: Text('${(c.probability * 100).toStringAsFixed(0)}%'),
                onTap: () => Navigator.pop(ctx, c),
              ),
          ],
        ),
      );
      if (chosen != null && mounted) {
        setState(() {
          _speciesController.text = chosen.scientificName;
          if (chosen.commonNames.isNotEmpty) _commonNameController.text = chosen.commonNames.first;
        });
      }
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Re-identify failed: $e')));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _checkHealth() async {
    final plant = _plant;
    if (plant == null || plant.photos.isEmpty) return;
    setState(() => _busy = true);
    try {
      final photoId = plant.photos[_photoIndex.clamp(0, plant.photos.length - 1)].id;
      final bytes = await _api.fetchPhotoBytes(plant.id, photoId);
      final tempFile = File('${Directory.systemTemp.path}/health_${plant.id}_$photoId.jpg');
      await tempFile.writeAsBytes(bytes);

      final candidates = await _api.checkHealth(tempFile);
      if (!mounted) return;
      await showModalBottomSheet<void>(
        context: context,
        builder: (ctx) => ListView(
          shrinkWrap: true,
          children: [
            const Padding(
              padding: EdgeInsets.all(16),
              child: Text('Health check results', style: TextStyle(fontWeight: FontWeight.bold)),
            ),
            const Padding(
              padding: EdgeInsets.symmetric(horizontal: 16),
              child: Text(
                'Informational only, not a professional diagnosis. Pl@ntNet '
                'currently supports a limited list of diseases and pests.',
                style: TextStyle(fontSize: 12, color: Colors.grey),
              ),
            ),
            const SizedBox(height: 8),
            if (candidates.isEmpty)
              const Padding(
                padding: EdgeInsets.all(16),
                child: Text('No matches found for this photo.'),
              ),
            for (final c in candidates)
              ListTile(
                title: Text(c.displayLabel),
                trailing: Text('${(c.probability * 100).toStringAsFixed(0)}%'),
              ),
          ],
        ),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Health check failed: $e')));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _identifyVariety() async {
    final plant = _plant;
    if (plant == null || plant.photos.isEmpty) return;
    setState(() => _busy = true);
    try {
      final photoId = plant.photos[_photoIndex.clamp(0, plant.photos.length - 1)].id;
      final bytes = await _api.fetchPhotoBytes(plant.id, photoId);
      final tempFile = File('${Directory.systemTemp.path}/variety_${plant.id}_$photoId.jpg');
      await tempFile.writeAsBytes(bytes);

      final candidates = await _api.identifyVariety(tempFile, species: plant.speciesScientific);
      if (!mounted) return;
      if (candidates.isEmpty) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('No variety candidates found for this photo.')),
        );
        return;
      }
      final chosen = await showModalBottomSheet<VarietyCandidate>(
        context: context,
        builder: (ctx) => ListView(
          shrinkWrap: true,
          children: [
            const Padding(
              padding: EdgeInsets.all(16),
              child: Text('Pick the variety', style: TextStyle(fontWeight: FontWeight.bold)),
            ),
            for (final v in candidates)
              ListTile(
                title: Text(v.name),
                trailing: Text('${(v.probability * 100).toStringAsFixed(0)}%'),
                onTap: () => Navigator.pop(ctx, v),
              ),
          ],
        ),
      );
      if (chosen != null && mounted) {
        setState(() => _varietyController.text = chosen.name);
      }
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Variety ID failed: $e')));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _addPhoto(ImageSource source) async {
    final xfile = await _picker.pickImage(source: source, maxWidth: 1600, imageQuality: 85);
    if (xfile == null || !mounted) return;
    setState(() => _busy = true);
    try {
      final updated = await _api.addPhoto(widget.plantId, File(xfile.path));
      if (!mounted) return;
      setState(() {
        _plant = updated;
        _photoIndex = updated.photos.length - 1;
      });
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Adding photo failed: $e')));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _deleteCurrentPhoto() async {
    final plant = _plant;
    if (plant == null || plant.photos.isEmpty) return;
    final photo = plant.photos[_photoIndex];
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Delete this photo?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
          TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Delete')),
        ],
      ),
    );
    if (confirmed != true) return;
    setState(() => _busy = true);
    try {
      await _api.deletePhoto(widget.plantId, photo.id);
      await _load();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Delete photo failed: $e')));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _setCurrentAsPrimary() async {
    final plant = _plant;
    if (plant == null || plant.photos.isEmpty) return;
    final photo = plant.photos[_photoIndex];
    if (photo.isPrimary) return;
    setState(() => _busy = true);
    try {
      final updated = await _api.setPrimaryPhoto(widget.plantId, photo.id);
      if (!mounted) return;
      setState(() => _plant = updated);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Set primary failed: $e')));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  void _pickAddPhotoSource() {
    showModalBottomSheet(
      context: context,
      builder: (ctx) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: const Icon(Icons.camera_alt),
              title: const Text('Take a photo'),
              onTap: () {
                Navigator.pop(ctx);
                _addPhoto(ImageSource.camera);
              },
            ),
            ListTile(
              leading: const Icon(Icons.photo_library),
              title: const Text('Choose from gallery'),
              onTap: () {
                Navigator.pop(ctx);
                _addPhoto(ImageSource.gallery);
              },
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _delete() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Delete plant?'),
        content: const Text('The vault note will be archived, not permanently removed.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
          TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Delete')),
        ],
      ),
    );
    if (confirmed != true) return;
    await _api.deletePlant(widget.plantId);
    if (mounted) Navigator.of(context).pop(true);
  }

  Widget _careField(String label, TextEditingController controller) {
    if (!_editing && controller.text.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: _editing
          ? TextField(
              controller: controller,
              decoration: InputDecoration(labelText: label, border: const OutlineInputBorder()),
            )
          : Text('$label: ${controller.text}'),
    );
  }

  Widget _photoGallery(Plant plant) {
    if (plant.photos.isEmpty) {
      return ClipRRect(
        borderRadius: BorderRadius.circular(12),
        child: Container(
          height: 200,
          color: const Color(0x11000000),
          child: const Center(child: Icon(Icons.eco_outlined, size: 40)),
        ),
      );
    }
    return Column(
      children: [
        ClipRRect(
          borderRadius: BorderRadius.circular(12),
          child: SizedBox(
            height: 220,
            child: PageView.builder(
              controller: _pageController,
              itemCount: plant.photos.length,
              onPageChanged: (i) => setState(() => _photoIndex = i),
              itemBuilder: (context, i) =>
                  AuthenticatedImage(plantId: plant.id, photoId: plant.photos[i].id),
            ),
          ),
        ),
        const SizedBox(height: 8),
        if (plant.photos.length > 1)
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              for (var i = 0; i < plant.photos.length; i++)
                Container(
                  margin: const EdgeInsets.symmetric(horizontal: 3),
                  width: 7,
                  height: 7,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: i == _photoIndex
                        ? Theme.of(context).colorScheme.primary
                        : Theme.of(context).colorScheme.primary.withValues(alpha: 0.25),
                  ),
                ),
            ],
          ),
        const SizedBox(height: 4),
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            TextButton.icon(
              onPressed: _busy ? null : _pickAddPhotoSource,
              icon: const Icon(Icons.add_a_photo_outlined),
              label: const Text('Add'),
            ),
            TextButton.icon(
              onPressed: _busy ? null : _checkHealth,
              icon: const Icon(Icons.health_and_safety_outlined),
              label: const Text('Check health'),
            ),
            if (plant.photos.length > 1)
              TextButton.icon(
                onPressed: _busy || plant.photos[_photoIndex].isPrimary ? null : _setCurrentAsPrimary,
                icon: const Icon(Icons.star_outline),
                label: const Text('Set primary'),
              ),
            TextButton.icon(
              onPressed: _busy ? null : _deleteCurrentPhoto,
              icon: const Icon(Icons.delete_outline),
              label: const Text('Delete'),
            ),
          ],
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    final plant = _plant;
    if (plant == null) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    return Scaffold(
      appBar: AppBar(
        title: Text(plant.displayName),
        actions: [
          IconButton(
            icon: Icon(_editing ? Icons.close : Icons.edit),
            onPressed: _busy ? null : () => setState(() => _editing = !_editing),
          ),
          IconButton(icon: const Icon(Icons.delete_outline), onPressed: _busy ? null : _delete),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          _photoGallery(plant),
          const SizedBox(height: 12),
          if (_editing) ...[
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: TextField(
                    controller: _speciesController,
                    decoration: const InputDecoration(
                      labelText: 'Species (scientific name)',
                      border: OutlineInputBorder(),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Padding(
                  padding: const EdgeInsets.only(top: 4),
                  child: OutlinedButton(
                    onPressed: _busy || plant.photos.isEmpty ? null : _reidentify,
                    child: const Text('Re-ID'),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: TextField(
                    controller: _varietyController,
                    decoration: const InputDecoration(
                      labelText: 'Variety / cultivar',
                      border: OutlineInputBorder(),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Padding(
                  padding: const EdgeInsets.only(top: 4),
                  child: OutlinedButton(
                    onPressed: _busy || plant.photos.isEmpty ? null : _identifyVariety,
                    child: const Text('ID'),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
          ] else if (plant.speciesScientific != null) ...[
            Text(plant.speciesScientific!, style: const TextStyle(fontStyle: FontStyle.italic)),
            if (plant.variety != null && plant.variety!.isNotEmpty)
              Text(plant.variety!, style: const TextStyle(fontStyle: FontStyle.italic, fontSize: 13)),
            const SizedBox(height: 12),
          ],
          if (_editing) ...[
            TextField(
              controller: _commonNameController,
              decoration: const InputDecoration(labelText: 'Common name', border: OutlineInputBorder()),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: _collectionController,
              decoration: const InputDecoration(labelText: 'Collection', border: OutlineInputBorder()),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: _tagsController,
              decoration: const InputDecoration(labelText: 'Tags (comma separated)', border: OutlineInputBorder()),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: _quantityController,
              decoration: const InputDecoration(labelText: 'Quantity', border: OutlineInputBorder()),
              keyboardType: TextInputType.number,
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
            const SizedBox(height: 8),
            TextField(
              controller: _notesController,
              decoration: const InputDecoration(labelText: 'Notes', border: OutlineInputBorder()),
              maxLines: 3,
            ),
          ] else ...[
            Wrap(
              spacing: 6,
              children: [
                if (plant.genus != null) Chip(label: Text(plant.genus!), avatar: const Icon(Icons.eco, size: 16)),
                if (plant.collection != null) Chip(label: Text(plant.collection!)),
                for (final t in plant.tags) Chip(label: Text(t)),
              ],
            ),
            const SizedBox(height: 8),
            Text('Quantity: ${plant.quantity}'),
            if (plant.forSale)
              Text('For sale${plant.priceCents != null ? ' — \$${(plant.priceCents! / 100).toStringAsFixed(2)}' : ''}'),
            if (plant.userNotes != null && plant.userNotes!.isNotEmpty) ...[
              const SizedBox(height: 8),
              Text(plant.userNotes!),
            ],
          ],
          const Divider(height: 32),
          Row(
            children: [
              const Text('Care', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
              const Spacer(),
              if (!_editing)
                TextButton.icon(
                  onPressed: _busy ? null : _regenerateCare,
                  icon: const Icon(Icons.refresh),
                  label: const Text('Regenerate'),
                ),
            ],
          ),
          _careField('Light', _careLightController),
          _careField('Water', _careWaterController),
          _careField('Soil', _careSoilController),
          _careField('Temperature', _careTemperatureController),
          _careField('Humidity', _careHumidityController),
          _careField('Fertilizer', _careFertilizerController),
          const SizedBox(height: 24),
          if (_editing)
            FilledButton(
              onPressed: _busy ? null : _save,
              child: _busy
                  ? const SizedBox(height: 16, width: 16, child: CircularProgressIndicator(strokeWidth: 2))
                  : const Text('Save changes'),
            ),
        ],
      ),
    );
  }
}
