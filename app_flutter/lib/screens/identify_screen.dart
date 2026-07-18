import 'dart:io';

import 'package:flutter/material.dart';

import '../api_client.dart';
import '../models/plant.dart';
import 'detail_screen.dart';
import 'save_screen.dart';

class IdentifyScreen extends StatelessWidget {
  final File photo;
  final List<IdentifyCandidate> candidates;

  IdentifyScreen({super.key, required this.photo, required this.candidates});

  final _api = ApiClient();

  Future<Plant?> _findExistingMatch(String scientificName) async {
    try {
      final matches = await _api.listPlants(q: scientificName);
      final needle = scientificName.trim().toLowerCase();
      for (final plant in matches) {
        if ((plant.speciesScientific ?? '').trim().toLowerCase() == needle) return plant;
      }
    } catch (_) {
      // If the lookup fails, fall through to the normal "create new" flow
      // rather than blocking the save on a non-essential check.
    }
    return null;
  }

  Future<void> _addToExisting(BuildContext context, Plant existing) async {
    final updated = await _api.updatePlant(existing.id, {'quantity': existing.quantity + 1});
    await _api.addPhoto(updated.id, photo);
    if (!context.mounted) return;
    await Navigator.of(context).pushAndRemoveUntil(
      MaterialPageRoute(builder: (_) => DetailScreen(plantId: existing.id)),
      (route) => route.isFirst,
    );
  }

  Future<void> _createNew(BuildContext context, IdentifyCandidate? candidate) async {
    String? variety;
    if (candidate != null) {
      variety = await _pickVariety(context, candidate.scientificName);
      if (!context.mounted) return;
    }
    // A successful save further down this flow uses pushAndRemoveUntil to
    // jump straight back to the catalog, clearing this screen along with
    // it — so there's nothing to do with the result here.
    await Navigator.of(context).push<void>(
      MaterialPageRoute(
        builder: (_) => SaveScreen(
          photo: photo,
          speciesScientific: candidate?.scientificName,
          commonName: candidate?.commonNames.isNotEmpty == true ? candidate!.commonNames.first : null,
          idConfidence: candidate?.probability,
          idSource: candidate != null ? 'plantnet' : null,
          variety: variety,
        ),
      ),
    );
  }

  Future<String?> _pickVariety(BuildContext context, String scientificName) async {
    List<VarietyCandidate> candidates;
    try {
      candidates = await _api.identifyVariety(photo, species: scientificName);
    } catch (_) {
      // Non-essential step; don't block the save flow on a failure.
      return null;
    }
    if (candidates.isEmpty || !context.mounted) return null;
    return showModalBottomSheet<String>(
      context: context,
      builder: (ctx) => ListView(
        shrinkWrap: true,
        children: [
          const Padding(
            padding: EdgeInsets.all(16),
            child: Text('Refine variety (optional)', style: TextStyle(fontWeight: FontWeight.bold)),
          ),
          for (final v in candidates)
            ListTile(
              title: Text(v.name),
              trailing: Text('${(v.probability * 100).toStringAsFixed(0)}%'),
              onTap: () => Navigator.pop(ctx, v.name),
            ),
          ListTile(
            title: const Text('Skip'),
            onTap: () => Navigator.pop(ctx, null),
          ),
        ],
      ),
    );
  }

  Future<void> _choose(BuildContext context, IdentifyCandidate? candidate) async {
    if (candidate == null) {
      await _createNew(context, null);
      return;
    }

    final existing = await _findExistingMatch(candidate.scientificName);
    if (!context.mounted) return;

    if (existing == null) {
      await _createNew(context, candidate);
      return;
    }

    final addToExisting = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Already in your catalog'),
        content: Text(
          'You already have "${existing.displayName}" (qty ${existing.quantity}). '
          'Add one more to it, or create a separate entry?',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Create separate entry'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Add to existing'),
          ),
        ],
      ),
    );
    if (!context.mounted) return;

    if (addToExisting == true) {
      await _addToExisting(context, existing);
    } else {
      await _createNew(context, candidate);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Confirm species')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          ClipRRect(
            borderRadius: BorderRadius.circular(12),
            child: Image.file(photo, height: 200, fit: BoxFit.cover, width: double.infinity),
          ),
          const SizedBox(height: 16),
          for (final c in candidates)
            Card(
              child: ListTile(
                title: Text(c.scientificName, style: const TextStyle(fontStyle: FontStyle.italic)),
                subtitle: Text(
                  c.commonNames.isNotEmpty ? c.commonNames.join(', ') : 'No common name',
                ),
                trailing: Text('${(c.probability * 100).toStringAsFixed(0)}%'),
                onTap: () => _choose(context, c),
              ),
            ),
          const SizedBox(height: 8),
          OutlinedButton(
            onPressed: () => _choose(context, null),
            child: const Text('None of these — enter manually'),
          ),
        ],
      ),
    );
  }
}
