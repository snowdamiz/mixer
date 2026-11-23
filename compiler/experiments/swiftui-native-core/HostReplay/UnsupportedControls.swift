import SwiftUI

func baselineStack() -> some View {
    HStack(alignment: .firstTextBaseline) { Text("Baseline") } // refused
}

func multilineField(_ text: Binding<String>) -> some View {
    TextField("Notes", text: text, axis: .vertical) // refused
}

func promptedField(_ text: Binding<String>) -> some View {
    TextField("Name", text: text, prompt: Text("Example")) // refused
}

func selectableList(_ selection: Binding<Int?>) -> some View {
    List(selection: selection) { Text("Row") } // refused
}

func customHeader() -> some View {
    Section { Text("Row") } header: { HStack { Text("Custom") } } // refused
}

func customToggle(_ value: Binding<Bool>) -> some View {
    Toggle(isOn: value) { HStack { Text("Custom") } } // refused
}
