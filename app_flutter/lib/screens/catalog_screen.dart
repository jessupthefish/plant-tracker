import 'package:flutter/material.dart';

import '../api_client.dart';
import '../models/plant.dart';
import '../widgets/authenticated_image.dart';
import 'capture_screen.dart';
import 'detail_screen.dart';
import 'settings_screen.dart';

class CatalogScreen extends StatefulWidget {
  const CatalogScreen({super.key});

  @override
  State<CatalogScreen> createState() => _CatalogScreenState();
}

class _CatalogScreenState extends State<CatalogScreen> {
  static const _sortOptions = {
    '-date_added': 'Newest first',
    'name': 'Name A-Z',
    '-quantity': 'Quantity (high to low)',
  };

  final _api = ApiClient();
  final _searchController = TextEditingController();
  List<Plant> _plants = [];
  bool _loading = true;
  String? _error;
  String? _collectionFilter;
  String? _genusFilter;
  bool? _forSaleFilter;
  String _sort = '-date_added';
  List<String> _collections = [];
  List<String> _genera = [];

  @override
  void initState() {
    super.initState();
    _refresh();
  }

  Future<void> _refresh() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final plants = await _api.listPlants(
        collection: _collectionFilter,
        forSale: _forSaleFilter,
        genus: _genusFilter,
        sort: _sort,
        q: _searchController.text.trim().isEmpty ? null : _searchController.text.trim(),
      );
      final collections = await _api.listCollections();
      final genera = await _api.listGenera();
      if (!mounted) return;
      setState(() {
        _plants = plants;
        _collections = collections;
        _genera = genera;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = '$e';
        _loading = false;
      });
    }
  }

  Future<void> _openCapture() async {
    // The add-plant flow may land back here via a flattened pushAndRemoveUntil
    // rather than a plain pop, so a bool result can't be relied on — just
    // always refresh (an extra idempotent GET is harmless).
    await Navigator.of(context).push<void>(
      MaterialPageRoute(builder: (_) => const CaptureScreen()),
    );
    _refresh();
  }

  Future<void> _openDetail(String id) async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute(builder: (_) => DetailScreen(plantId: id)),
    );
    _refresh();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Plant Catalog'),
        actions: [
          PopupMenuButton<String>(
            icon: const Icon(Icons.sort),
            tooltip: 'Sort',
            initialValue: _sort,
            onSelected: (value) {
              setState(() => _sort = value);
              _refresh();
            },
            itemBuilder: (context) => [
              for (final entry in _sortOptions.entries)
                PopupMenuItem(value: entry.key, child: Text(entry.value)),
            ],
          ),
          IconButton(
            icon: const Icon(Icons.settings_outlined),
            onPressed: () => Navigator.of(context).push(
              MaterialPageRoute(builder: (_) => const SettingsScreen()),
            ),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _refresh,
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
              child: TextField(
                controller: _searchController,
                decoration: InputDecoration(
                  hintText: 'Search plants...',
                  prefixIcon: const Icon(Icons.search),
                  border: const OutlineInputBorder(),
                  isDense: true,
                ),
                onSubmitted: (_) => _refresh(),
              ),
            ),
            SizedBox(
              height: 40,
              child: ListView(
                scrollDirection: Axis.horizontal,
                padding: const EdgeInsets.symmetric(horizontal: 16),
                children: [
                  FilterChip(
                    label: const Text('All'),
                    selected: _collectionFilter == null && _forSaleFilter == null && _genusFilter == null,
                    onSelected: (_) {
                      setState(() {
                        _collectionFilter = null;
                        _forSaleFilter = null;
                        _genusFilter = null;
                      });
                      _refresh();
                    },
                  ),
                  const SizedBox(width: 8),
                  FilterChip(
                    label: const Text('For sale'),
                    selected: _forSaleFilter == true,
                    onSelected: (selected) {
                      setState(() => _forSaleFilter = selected ? true : null);
                      _refresh();
                    },
                  ),
                  const SizedBox(width: 8),
                  for (final c in _collections) ...[
                    FilterChip(
                      label: Text(c),
                      selected: _collectionFilter == c,
                      onSelected: (selected) {
                        setState(() => _collectionFilter = selected ? c : null);
                        _refresh();
                      },
                    ),
                    const SizedBox(width: 8),
                  ],
                ],
              ),
            ),
            if (_genera.isNotEmpty) ...[
              const SizedBox(height: 8),
              SizedBox(
                height: 40,
                child: ListView(
                  scrollDirection: Axis.horizontal,
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  children: [
                    for (final g in _genera) ...[
                      FilterChip(
                        avatar: const Icon(Icons.eco, size: 16),
                        label: Text(g),
                        selected: _genusFilter == g,
                        onSelected: (selected) {
                          setState(() => _genusFilter = selected ? g : null);
                          _refresh();
                        },
                      ),
                      const SizedBox(width: 8),
                    ],
                  ],
                ),
              ),
            ],
            const SizedBox(height: 8),
            Expanded(child: _buildBody()),
          ],
        ),
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _openCapture,
        icon: const Icon(Icons.add_a_photo),
        label: const Text('Add plant'),
      ),
    );
  }

  Widget _buildBody() {
    if (_loading) return const Center(child: CircularProgressIndicator());
    if (_error != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.cloud_off, size: 40),
              const SizedBox(height: 8),
              Text('Could not reach the backend.\n$_error', textAlign: TextAlign.center),
              const SizedBox(height: 12),
              OutlinedButton(onPressed: _refresh, child: const Text('Retry')),
            ],
          ),
        ),
      );
    }
    if (_plants.isEmpty) {
      return const Center(child: Text('No plants yet. Tap "Add plant" to get started.'));
    }
    return GridView.builder(
      padding: const EdgeInsets.all(16),
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 2,
        mainAxisSpacing: 12,
        crossAxisSpacing: 12,
        childAspectRatio: 0.8,
      ),
      itemCount: _plants.length,
      itemBuilder: (context, index) {
        final plant = _plants[index];
        return GestureDetector(
          onTap: () => _openDetail(plant.id),
          child: Card(
            clipBehavior: Clip.antiAlias,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Expanded(
                  child: plant.photos.isNotEmpty
                      ? AuthenticatedImage(plantId: plant.id, photoId: plant.photos.first.id)
                      : const ColoredBox(
                          color: Color(0x11000000),
                          child: Icon(Icons.eco_outlined, size: 40),
                        ),
                ),
                Padding(
                  padding: const EdgeInsets.all(8),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(plant.displayName,
                          maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.bold)),
                      Text('Qty ${plant.quantity}${plant.forSale ? ' · For sale' : ''}',
                          style: Theme.of(context).textTheme.bodySmall),
                    ],
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}
