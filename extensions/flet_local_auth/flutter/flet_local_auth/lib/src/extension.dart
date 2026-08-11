import 'package:flet/flet.dart';

import 'local_auth_service.dart';

class Extension extends FletExtension {
  @override
  FletService? createService(Control control) {
    switch (control.type) {
      case "FinanseLocalAuth":
        return FinanseLocalAuthService(control: control);
      default:
        return null;
    }
  }
}
