import 'package:flet/flet.dart';
import 'package:flutter/widgets.dart';

import 'local_auth_service.dart';

class Extension extends FletExtension {
  @override
  void ensureInitialized() {}

  @override
  FletService? createService(Control control) {
    switch (control.type) {
      case "FinanseLocalAuth":
        return FinanseLocalAuthService(control: control);
      default:
        return null;
    }
  }

  @override
  Widget? createWidget(Key? key, Control control) {
    return null;
  }
}
