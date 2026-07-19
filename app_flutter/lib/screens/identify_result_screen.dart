import 'dart:io';

import 'package:flutter/material.dart';

import '../models/plant.dart';

const _sourceExplanations = {
  'catalog': 'Matches a plant already in your collection, so the name stays consistent.',
  'inaturalist':
      'iNaturalist — a community-run naturalist database used by scientists and hobbyists to record and identify species.',
  'gbif_vernacular':
      'GBIF (Global Biodiversity Information Facility) — an international scientific database of species names.',
  'plantnet_fallback': "Pl@ntNet — the same service that matched your photo to this species.",
  'wikipedia': 'Wikipedia.',
};

class IdentifyResultScreen extends StatelessWidget {
  final File photo;
  final IdentifyCandidate? candidate;
  final SpeciesEnrichment? enrichment;
  final Future<void> Function() onSave;

  const IdentifyResultScreen({
    super.key,
    required this.photo,
    required this.candidate,
    this.enrichment,
    required this.onSave,
  });

  void _showSourcesInfo(BuildContext context) {
    final e = enrichment;
    if (e == null) return;
    final rows = <MapEntry<String, String>>[
      if (e.commonNameSource != null) MapEntry('Common name', e.commonNameSource!),
      if (e.descriptionSource != null) MapEntry('Description', e.descriptionSource!),
      for (final source in e.photos.map((p) => p.source).toSet()) MapEntry('Photo', source),
    ];
    showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Where this data comes from'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Your photo was matched to a species using Pl@ntNet. The details below are '
                'cross-referenced from independent scientific databases by scientific name.',
              ),
              const SizedBox(height: 12),
              for (final row in rows)
                Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Text.rich(
                    TextSpan(children: [
                      TextSpan(text: '${row.key}: ', style: const TextStyle(fontWeight: FontWeight.bold)),
                      TextSpan(text: _sourceExplanations[row.value] ?? row.value),
                    ]),
                  ),
                ),
            ],
          ),
        ),
        actions: [TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Got it'))],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final candidate = this.candidate;
    final enrichment = this.enrichment;
    return Scaffold(
      appBar: AppBar(
        title: const Text('Identification result'),
        actions: [
          if (enrichment != null)
            IconButton(
              icon: const Icon(Icons.info_outline),
              tooltip: 'Where this data comes from',
              onPressed: () => _showSourcesInfo(context),
            ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          ClipRRect(
            borderRadius: BorderRadius.circular(12),
            child: Image.file(photo, height: 200, fit: BoxFit.cover, width: double.infinity),
          ),
          const SizedBox(height: 16),
          if (candidate == null)
            const Text('No match found for this photo.')
          else ...[
            Text(
              candidate.scientificName,
              style: const TextStyle(fontStyle: FontStyle.italic, fontSize: 18),
            ),
            const SizedBox(height: 4),
            Text(enrichment?.commonName ?? candidate.commonName ?? 'No common name'),
            const SizedBox(height: 4),
            Text('${(candidate.probability * 100).toStringAsFixed(0)}% match'),
            if (enrichment?.description != null) ...[
              const SizedBox(height: 12),
              Text(enrichment!.description!),
            ],
            if (enrichment != null && enrichment.photos.isNotEmpty) ...[
              const SizedBox(height: 12),
              SizedBox(
                height: 100,
                child: ListView(
                  scrollDirection: Axis.horizontal,
                  children: [
                    for (final p in enrichment.photos)
                      Padding(
                        padding: const EdgeInsets.only(right: 8),
                        child: ClipRRect(
                          borderRadius: BorderRadius.circular(8),
                          child: Image.network(
                            p.url,
                            width: 100,
                            height: 100,
                            fit: BoxFit.cover,
                            errorBuilder: (_, _, _) => const SizedBox.shrink(),
                          ),
                        ),
                      ),
                  ],
                ),
              ),
            ],
          ],
          const SizedBox(height: 24),
          OutlinedButton(
            onPressed: () => Navigator.of(context).popUntil((route) => route.isFirst),
            child: const Text('Done'),
          ),
          const SizedBox(height: 12),
          FilledButton(
            onPressed: () => onSave(),
            child: const Text('Save this plant'),
          ),
        ],
      ),
    );
  }
}
