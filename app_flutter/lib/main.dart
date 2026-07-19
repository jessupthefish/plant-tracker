import 'package:flutter/material.dart';

import 'screens/catalog_screen.dart';

void main() {
  runApp(const PlantTrackerApp());
}

class PlantTrackerApp extends StatelessWidget {
  const PlantTrackerApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'NOIDChonk',
      theme: ThemeData(colorScheme: ColorScheme.fromSeed(seedColor: Colors.green)),
      home: const CatalogScreen(),
    );
  }
}
