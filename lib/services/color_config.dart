import 'package:flutter/material.dart';

class AppColors {
  // Status colors - preserved from original design
  static Color get successColor => Colors.green;
  static Color get warningColor => Colors.orange;
  static Color get errorColor => Colors.red;
  static Color get statusMessageBackground => Colors.white;
  static Color get statusMessageText => Colors.black;
  
  // Dark theme - main backgrounds
  static Color get primaryBackground => Colors.blueGrey[900]!; // Main dark background
  static Color get secondaryBackground => Colors.blueGrey[800]!; // Card background (slightly lighter)
  static Color get drawerBackground => Colors.blueGrey[900]!; // Same as primary
  static Color get cardBackground => Colors.blueGrey[800]!; // Same as secondary
  static Color get dialogBackground => Colors.blueGrey[900]!; // Dialog background
  
  // Dark theme - text colors
  static Color get primaryText => Colors.grey[300]!; // Main text color (light gray)
  static Color get secondaryText => Colors.grey[400]!; // Muted text (darker gray)
  static Color get tertiaryText => Colors.grey[500]!; // Even more muted text
  
  // Input field colors
  static Color get inputText => Colors.grey[300]!; // User-typed text
  static Color get inputLabel => Colors.grey[500]!; // Field labels
  static Color get inputHint => Colors.grey[600]!; // Placeholder text
  static Color get inputHelper => Colors.grey[500]!; // Helper text
  static Color get inputIcon => Colors.grey[500]!; // Input field icons
  
  // Accent colors for selected states and highlights
  static Color get selectedBlue => Colors.blue[300]!; // For selected menu items
  static Color get accentBlue => Colors.blue; // For storage icons, etc.
  static Color get accentGreen => Colors.green; // For webhook icons, success states
  static Color get accentRed => Colors.red; // For delete buttons, error states
  static Color get accentOrange => Colors.orange[300]!; // For warning text
  
  // App bar (can be customized separately if needed)
  static Color get appBarBackground => Colors.blue;
  static Color get appBarText => Colors.white;
  
  static void initialize() {
    // Simple initialization - no complex loading for now
    print('AppColors initialized with dark theme');
  }
}