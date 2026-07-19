import 'dart:convert';
import 'dart:io';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;

import 'models/plant.dart';

class ApiException implements Exception {
  final String message;
  ApiException(this.message);

  @override
  String toString() => message;
}

/// Talks to the Plant Tracker backend. Base URL and bearer token are
/// user-configurable at runtime (Settings screen) since they change between
/// local dev and the deployed Cloudflare Tunnel URL.
class ApiClient {
  static const _storage = FlutterSecureStorage();
  static const _baseUrlKey = 'api_base_url';
  static const _tokenKey = 'api_bearer_token';

  static Future<String?> getBaseUrl() => _storage.read(key: _baseUrlKey);
  static Future<void> setBaseUrl(String url) =>
      _storage.write(key: _baseUrlKey, value: url.trim());

  static Future<String?> getToken() => _storage.read(key: _tokenKey);
  static Future<void> setToken(String token) =>
      _storage.write(key: _tokenKey, value: token.trim());

  static const _locationKey = 'user_location';
  static Future<String?> getLocation() => _storage.read(key: _locationKey);
  static Future<void> setLocation(String location) =>
      _storage.write(key: _locationKey, value: location.trim());

  Future<Map<String, String>> _headers() async {
    final token = await getToken();
    return {
      if (token != null && token.isNotEmpty) 'Authorization': 'Bearer $token',
    };
  }

  Future<Uri> _uri(String path, [Map<String, String>? query]) async {
    final base = await getBaseUrl();
    if (base == null || base.isEmpty) {
      throw ApiException('No backend URL configured. Set it in Settings.');
    }
    return Uri.parse('$base$path').replace(queryParameters: query);
  }

  Future<T> _handle<T>(http.Response response, T Function(dynamic) onOk) async {
    if (response.statusCode >= 200 && response.statusCode < 300) {
      final body = response.body.isEmpty ? null : jsonDecode(response.body);
      return onOk(body);
    }
    throw ApiException('Request failed (${response.statusCode}): ${response.body}');
  }

  Future<List<IdentifyCandidate>> identify(File photo) async {
    final uri = await _uri('/api/v1/identify');
    final request = http.MultipartRequest('POST', uri)
      ..headers.addAll(await _headers())
      ..files.add(await http.MultipartFile.fromPath('photo', photo.path));
    final streamed = await request.send();
    final response = await http.Response.fromStream(streamed);
    return _handle(response, (body) => (body['candidates'] as List)
        .map((e) => IdentifyCandidate.fromJson(e as Map<String, dynamic>))
        .toList());
  }

  Future<SpeciesEnrichment> enrichSpecies(
    String scientificName, {
    String? commonName,
    String? locale,
    String? country,
  }) async {
    final query = <String, String>{
      'scientific_name': scientificName,
      if (commonName != null && commonName.isNotEmpty) 'common_name': commonName,
      if (locale != null && locale.isNotEmpty) 'locale': locale,
      if (country != null && country.isNotEmpty) 'country': country,
    };
    final uri = await _uri('/api/v1/species/enrich', query);
    final response =
        await http.get(uri, headers: await _headers()).timeout(const Duration(seconds: 12));
    return _handle(response, (body) => SpeciesEnrichment.fromJson(body as Map<String, dynamic>));
  }

  Future<List<DiseaseCandidate>> checkHealth(File photo) async {
    final uri = await _uri('/api/v1/check-health');
    final request = http.MultipartRequest('POST', uri)
      ..headers.addAll(await _headers())
      ..files.add(await http.MultipartFile.fromPath('photo', photo.path));
    final streamed = await request.send();
    final response = await http.Response.fromStream(streamed);
    return _handle(response, (body) => (body['candidates'] as List)
        .map((e) => DiseaseCandidate.fromJson(e as Map<String, dynamic>))
        .toList());
  }

  Future<List<VarietyCandidate>> identifyVariety(File photo, {String? species}) async {
    final uri = await _uri('/api/v1/identify-variety');
    final request = http.MultipartRequest('POST', uri)
      ..headers.addAll(await _headers())
      ..files.add(await http.MultipartFile.fromPath('photo', photo.path));
    if (species != null && species.isNotEmpty) request.fields['species'] = species;
    final streamed = await request.send();
    final response = await http.Response.fromStream(streamed);
    return _handle(response, (body) => (body['candidates'] as List)
        .map((e) => VarietyCandidate.fromJson(e as Map<String, dynamic>))
        .toList());
  }

  Future<Plant> createPlant({
    String? speciesScientific,
    String? commonName,
    String? variety,
    String? collection,
    List<String> tags = const [],
    int quantity = 1,
    bool forSale = false,
    int? priceCents,
    String? userNotes,
    double? idConfidence,
    String? idSource,
    File? photo,
  }) async {
    final uri = await _uri('/api/v1/plants');
    final request = http.MultipartRequest('POST', uri)..headers.addAll(await _headers());
    void addField(String key, String? value) {
      if (value != null) request.fields[key] = value;
    }

    addField('species_scientific', speciesScientific);
    addField('common_name', commonName);
    addField('variety', variety);
    addField('collection', collection);
    request.fields['tags'] = tags.join(',');
    request.fields['quantity'] = quantity.toString();
    request.fields['for_sale'] = forSale.toString();
    addField('price_cents', priceCents?.toString());
    addField('user_notes', userNotes);
    addField('id_confidence', idConfidence?.toString());
    addField('id_source', idSource);
    if (photo != null) {
      request.files.add(await http.MultipartFile.fromPath('photo', photo.path));
    }
    final streamed = await request.send();
    final response = await http.Response.fromStream(streamed);
    return _handle(response, (body) => Plant.fromJson(body as Map<String, dynamic>));
  }

  Future<List<Plant>> listPlants({
    String? collection,
    String? tag,
    bool? forSale,
    String? genus,
    String? q,
    String? sort,
  }) async {
    final query = <String, String>{
      if (collection != null) 'collection': collection,
      if (tag != null) 'tag': tag,
      if (forSale != null) 'for_sale': forSale.toString(),
      if (genus != null) 'genus': genus,
      if (q != null && q.isNotEmpty) 'q': q,
      if (sort != null) 'sort': sort,
    };
    final uri = await _uri('/api/v1/plants', query);
    final response = await http.get(uri, headers: await _headers());
    return _handle(
        response,
        (body) =>
            (body as List).map((e) => Plant.fromJson(e as Map<String, dynamic>)).toList());
  }

  Future<Plant> getPlant(String id) async {
    final uri = await _uri('/api/v1/plants/$id');
    final response = await http.get(uri, headers: await _headers());
    return _handle(response, (body) => Plant.fromJson(body as Map<String, dynamic>));
  }

  Future<Plant> updatePlant(String id, Map<String, dynamic> patch) async {
    final uri = await _uri('/api/v1/plants/$id');
    final headers = await _headers();
    headers['Content-Type'] = 'application/json';
    final response = await http.patch(uri, headers: headers, body: jsonEncode(patch));
    return _handle(response, (body) => Plant.fromJson(body as Map<String, dynamic>));
  }

  Future<void> deletePlant(String id) async {
    final uri = await _uri('/api/v1/plants/$id');
    final response = await http.delete(uri, headers: await _headers());
    await _handle(response, (_) => null);
  }

  Future<Plant> regenerateCare(String id) async {
    final uri = await _uri('/api/v1/plants/$id/regenerate-care');
    final response = await http.post(uri, headers: await _headers());
    return _handle(response, (body) => Plant.fromJson(body as Map<String, dynamic>));
  }

  Future<List<String>> listTags() async {
    final uri = await _uri('/api/v1/tags');
    final response = await http.get(uri, headers: await _headers());
    return _handle(response, (body) => (body as List).map((e) => e as String).toList());
  }

  Future<List<String>> listCollections() async {
    final uri = await _uri('/api/v1/collections');
    final response = await http.get(uri, headers: await _headers());
    return _handle(response, (body) => (body as List).map((e) => e as String).toList());
  }

  Future<List<String>> listGenera() async {
    final uri = await _uri('/api/v1/genera');
    final response = await http.get(uri, headers: await _headers());
    return _handle(response, (body) => (body as List).map((e) => e as String).toList());
  }

  Future<Plant> addPhoto(String plantId, File photo) async {
    final uri = await _uri('/api/v1/plants/$plantId/photos');
    final request = http.MultipartRequest('POST', uri)
      ..headers.addAll(await _headers())
      ..files.add(await http.MultipartFile.fromPath('photo', photo.path));
    final streamed = await request.send();
    final response = await http.Response.fromStream(streamed);
    await _handle(response, (_) => null);
    return getPlant(plantId);
  }

  Future<void> deletePhoto(String plantId, String photoId) async {
    final uri = await _uri('/api/v1/plants/$plantId/photos/$photoId');
    final response = await http.delete(uri, headers: await _headers());
    await _handle(response, (_) => null);
  }

  Future<Plant> setPrimaryPhoto(String plantId, String photoId) async {
    final uri = await _uri('/api/v1/plants/$plantId/photos/$photoId/set-primary');
    final response = await http.post(uri, headers: await _headers());
    return _handle(response, (body) => Plant.fromJson(body as Map<String, dynamic>));
  }

  Future<bool> health() async {
    try {
      final uri = await _uri('/api/v1/health');
      final response = await http.get(uri, headers: await _headers()).timeout(
            const Duration(seconds: 5),
          );
      return response.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  Future<List<int>> fetchPhotoBytes(String plantId, String photoId) async {
    final uri = await _uri('/api/v1/plants/$plantId/photos/$photoId');
    final response = await http.get(uri, headers: await _headers());
    if (response.statusCode != 200) {
      throw ApiException('Failed to load photo (${response.statusCode})');
    }
    return response.bodyBytes;
  }
}
