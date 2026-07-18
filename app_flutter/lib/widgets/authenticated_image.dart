import 'dart:typed_data';

import 'package:flutter/material.dart';

import '../api_client.dart';

/// Plant photos are served behind the bearer-token auth dependency, so a
/// plain Image.network (no custom headers) can't load them — fetch bytes
/// via the authenticated ApiClient instead and render with Image.memory.
class AuthenticatedImage extends StatelessWidget {
  final String plantId;
  final String photoId;
  final BoxFit fit;

  const AuthenticatedImage({
    super.key,
    required this.plantId,
    required this.photoId,
    this.fit = BoxFit.cover,
  });

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<int>>(
      future: ApiClient().fetchPhotoBytes(plantId, photoId),
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const ColoredBox(
            color: Color(0x11000000),
            child: Center(child: CircularProgressIndicator(strokeWidth: 2)),
          );
        }
        if (snapshot.hasError || !snapshot.hasData) {
          return const ColoredBox(
            color: Color(0x11000000),
            child: Icon(Icons.eco_outlined),
          );
        }
        return Image.memory(Uint8List.fromList(snapshot.data!), fit: fit);
      },
    );
  }
}
