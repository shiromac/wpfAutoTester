using System.Windows;

namespace TestApp;

public partial class MainWindow : Window
{
    private int _clickCount;

    public MainWindow()
    {
        InitializeComponent();
    }

    private void MainButton_Click(object sender, RoutedEventArgs e)
    {
        _clickCount++;
        StatusLabel.Text = "Clicked";
        CounterLabel.Text = $"Clicks: {_clickCount}";
    }

    private void ResetButton_Click(object sender, RoutedEventArgs e)
    {
        _clickCount = 0;
        OptionCheck.IsChecked = false;
        StatusLabel.Text = "Ready";
        CounterLabel.Text = "Clicks: 0";
        InputField.Text = "";
    }

    private void OptionCheck_Changed(object sender, RoutedEventArgs e)
    {
        StatusLabel.Text = OptionCheck.IsChecked == true ? "Option enabled" : "Option disabled";
    }
}
