import 'package:flutter_test/flutter_test.dart';

import 'package:plant_tracker_app/main.dart';

void main() {
  testWidgets('App launches to the catalog screen', (WidgetTester tester) async {
    await tester.pumpWidget(const PlantTrackerApp());
    await tester.pump();

    expect(find.text('Plant Catalog'), findsOneWidget);
    expect(find.text('Add plant'), findsOneWidget);
  });
}
