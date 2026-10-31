export function Stepper({ steps = [], currentStep = 0 }) {
  return (
    <ol>
      {steps.map((step, index) => (
        <li key={step} style={{ fontWeight: index === currentStep ? 700 : 400 }}>
          {step}
        </li>
      ))}
    </ol>
  );
}
