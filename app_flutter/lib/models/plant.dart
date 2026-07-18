class Photo {
  final String id;
  final String filename;
  final bool isPrimary;

  Photo({required this.id, required this.filename, required this.isPrimary});

  factory Photo.fromJson(Map<String, dynamic> json) => Photo(
        id: json['id'] as String,
        filename: json['filename'] as String,
        isPrimary: json['is_primary'] as bool,
      );
}

class Plant {
  final String id;
  final String? speciesScientific;
  final String? genus;
  final String? commonName;
  final double? idConfidence;
  final String? idSource;
  final String? variety;
  final String? collection;
  final int quantity;
  final bool forSale;
  final int? priceCents;
  final String? careLight;
  final String? careWater;
  final String? careSoil;
  final String? careTemperature;
  final String? careHumidity;
  final String? careFertilizer;
  final String? careNotesExtra;
  final String? userNotes;
  final List<String> tags;
  final List<Photo> photos;
  final DateTime createdAt;
  final DateTime updatedAt;

  Plant({
    required this.id,
    this.speciesScientific,
    this.genus,
    this.commonName,
    this.idConfidence,
    this.idSource,
    this.variety,
    this.collection,
    required this.quantity,
    required this.forSale,
    this.priceCents,
    this.careLight,
    this.careWater,
    this.careSoil,
    this.careTemperature,
    this.careHumidity,
    this.careFertilizer,
    this.careNotesExtra,
    this.userNotes,
    required this.tags,
    required this.photos,
    required this.createdAt,
    required this.updatedAt,
  });

  String get displayName => commonName ?? speciesScientific ?? 'Unnamed plant';

  factory Plant.fromJson(Map<String, dynamic> json) => Plant(
        id: json['id'] as String,
        speciesScientific: json['species_scientific'] as String?,
        genus: json['genus'] as String?,
        commonName: json['common_name'] as String?,
        idConfidence: (json['id_confidence'] as num?)?.toDouble(),
        idSource: json['id_source'] as String?,
        variety: json['variety'] as String?,
        collection: json['collection'] as String?,
        quantity: json['quantity'] as int,
        forSale: json['for_sale'] as bool,
        priceCents: json['price_cents'] as int?,
        careLight: json['care_light'] as String?,
        careWater: json['care_water'] as String?,
        careSoil: json['care_soil'] as String?,
        careTemperature: json['care_temperature'] as String?,
        careHumidity: json['care_humidity'] as String?,
        careFertilizer: json['care_fertilizer'] as String?,
        careNotesExtra: json['care_notes_extra'] as String?,
        userNotes: json['user_notes'] as String?,
        tags: (json['tags'] as List).map((e) => e as String).toList(),
        photos: (json['photos'] as List)
            .map((e) => Photo.fromJson(e as Map<String, dynamic>))
            .toList(),
        createdAt: DateTime.parse(json['created_at'] as String),
        updatedAt: DateTime.parse(json['updated_at'] as String),
      );
}

class IdentifyCandidate {
  final String scientificName;
  final List<String> commonNames;
  final double probability;

  IdentifyCandidate({
    required this.scientificName,
    required this.commonNames,
    required this.probability,
  });

  factory IdentifyCandidate.fromJson(Map<String, dynamic> json) => IdentifyCandidate(
        scientificName: json['scientific_name'] as String,
        commonNames: (json['common_names'] as List).map((e) => e as String).toList(),
        probability: (json['probability'] as num).toDouble(),
      );
}

class DiseaseCandidate {
  final String name;
  final String? description;
  final double probability;

  DiseaseCandidate({required this.name, this.description, required this.probability});

  factory DiseaseCandidate.fromJson(Map<String, dynamic> json) => DiseaseCandidate(
        name: json['name'] as String,
        description: json['description'] as String?,
        probability: (json['probability'] as num).toDouble(),
      );

  String get displayLabel => (description?.isNotEmpty ?? false) ? description! : name;
}

class VarietyCandidate {
  final String name;
  final double probability;

  VarietyCandidate({required this.name, required this.probability});

  factory VarietyCandidate.fromJson(Map<String, dynamic> json) => VarietyCandidate(
        name: json['name'] as String,
        probability: (json['probability'] as num).toDouble(),
      );
}
