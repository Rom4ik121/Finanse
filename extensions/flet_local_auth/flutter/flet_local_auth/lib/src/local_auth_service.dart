import 'package:flet/flet.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:local_auth/local_auth.dart';
import 'package:local_auth_android/local_auth_android.dart';
import 'package:local_auth_darwin/local_auth_darwin.dart';

class FinanseLocalAuthService extends FletService {
  FinanseLocalAuthService({required super.control});

  final LocalAuthentication _auth = LocalAuthentication();

  @override
  void init() {
    super.init();
    debugPrint("FinanseLocalAuth(${control.id}).init");
    control.addInvokeMethodListener(_invokeMethod);
  }

  Future<dynamic> _invokeMethod(String name, dynamic args) async {
    debugPrint("FinanseLocalAuth.$name($args)");
    switch (name) {
      case "is_device_supported":
        return await _auth.isDeviceSupported();
      case "can_check_biometrics":
        return await _auth.canCheckBiometrics;
      case "get_available_biometrics":
        final types = await _auth.getAvailableBiometrics();
        return types.map((t) => t.name).toList();
      case "authenticate":
        return _authenticate(args);
      default:
        throw Exception("Unknown FinanseLocalAuth method: $name");
    }
  }

  Future<Map<String, dynamic>> _authenticate(dynamic args) async {
    final reason = (args?["reason"] as String?) ?? "Unlock";
    final biometricOnly = args?["biometric_only"] != false;

    try {
      final ok = await _auth.authenticate(
        localizedReason: reason,
        authMessages: const [
          AndroidAuthMessages(
            signInTitle: "Finanse",
            biometricHint: "",
            cancelButton: "Cancel",
          ),
          IOSAuthMessages(cancelButton: "Cancel"),
        ],
        options: AuthenticationOptions(
          biometricOnly: biometricOnly,
          stickyAuth: true,
          useErrorDialogs: true,
        ),
      );
      return {"ok": ok, "code": ok ? null : "failed"};
    } on PlatformException catch (error) {
      return {"ok": false, "code": error.code};
    } catch (error) {
      return {"ok": false, "code": error.toString()};
    }
  }

  @override
  void dispose() {
    control.removeInvokeMethodListener(_invokeMethod);
    super.dispose();
  }
}
