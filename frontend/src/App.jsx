import { useState } from "react";
import "./App.css";

// Step Components
import StepOrderVerification from "./components/StepOrderVerification";
import StepMethodSelection from "./components/StepMethodSelection";
import StepProductSelection from "./components/StepProductSelection";
import StepReturnReason from "./components/StepReturnReason";
import StepExchangeVariant from "./components/StepExchangeVariant";
import StepConfirmation from "./components/StepConfirmation";
import StepSuccess from "./components/StepSuccess";

// Chat Agent Component
import ChatAgent from "./components/ChatAgent";

const STEPS = {
  VERIFICATION: 1,
  METHOD: 2,
  PRODUCTS: 3,
  REASON: 4,
  EXCHANGE: 5,
  CONFIRMATION: 6,
  SUCCESS: 7
};

function App() {
  const [activeTab, setActiveTab] = useState("portal"); // portal, agent
  const [currentStep, setCurrentStep] = useState(STEPS.VERIFICATION);
  const [order, setOrder] = useState(null);
  const [orderNumber, setOrderNumber] = useState("");
  const [email, setEmail] = useState("");
  
  const [returnMethod, setReturnMethod] = useState(""); // refund, credit, exchange
  const [selectedItems, setSelectedItems] = useState({}); // { itemId: quantity }
  const [returnReasons, setReturnReasons] = useState({}); // { itemId: { reason, notes, image } }
  const [exchangeVariants, setExchangeVariants] = useState({}); // { itemId: { size, color } }
  const [submissionResult, setSubmissionResult] = useState(null);

  const handleRestart = () => {
    setCurrentStep(STEPS.VERIFICATION);
    setOrder(null);
    setOrderNumber("");
    setEmail("");
    setReturnMethod("");
    setSelectedItems({});
    setReturnReasons({});
    setExchangeVariants({});
    setSubmissionResult(null);
  };

  const navigateBack = () => {
    if (currentStep === STEPS.CONFIRMATION) {
      if (returnMethod === "exchange") {
        setCurrentStep(STEPS.EXCHANGE);
      } else {
        setCurrentStep(STEPS.REASON);
      }
    } else if (currentStep === STEPS.EXCHANGE) {
      setCurrentStep(STEPS.REASON);
    } else if (currentStep === STEPS.REASON) {
      setCurrentStep(STEPS.PRODUCTS);
    } else if (currentStep === STEPS.PRODUCTS) {
      setCurrentStep(STEPS.METHOD);
    } else if (currentStep === STEPS.METHOD) {
      setCurrentStep(STEPS.VERIFICATION);
    }
  };

  const renderStep = () => {
    switch (currentStep) {
      case STEPS.VERIFICATION:
        return (
          <StepOrderVerification
            initialOrderNumber={orderNumber}
            initialEmail={email}
            onNext={(matchedOrder, num, mail) => {
              setOrder(matchedOrder);
              setOrderNumber(num);
              setEmail(mail);
              setCurrentStep(STEPS.METHOD);
            }}
          />
        );
      case STEPS.METHOD:
        return (
          <StepMethodSelection
            initialMethod={returnMethod}
            onBack={navigateBack}
            onNext={(method) => {
              setReturnMethod(method);
              setCurrentStep(STEPS.PRODUCTS);
            }}
          />
        );
      case STEPS.PRODUCTS:
        return (
          <StepProductSelection
            order={order}
            initialSelectedItems={selectedItems}
            onBack={navigateBack}
            onNext={(items) => {
              setSelectedItems(items);
              setCurrentStep(STEPS.REASON);
            }}
          />
        );
      case STEPS.REASON:
        return (
          <StepReturnReason
            order={order}
            selectedItems={selectedItems}
            initialReasons={returnReasons}
            onBack={navigateBack}
            onNext={(reasons) => {
              setReturnReasons(reasons);
              if (returnMethod === "exchange") {
                setCurrentStep(STEPS.EXCHANGE);
              } else {
                setCurrentStep(STEPS.CONFIRMATION);
              }
            }}
          />
        );
      case STEPS.EXCHANGE:
        return (
          <StepExchangeVariant
            order={order}
            selectedItems={selectedItems}
            initialExchanges={exchangeVariants}
            onBack={navigateBack}
            onNext={(exchanges) => {
              setExchangeVariants(exchanges);
              setCurrentStep(STEPS.CONFIRMATION);
            }}
          />
        );
      case STEPS.CONFIRMATION:
        return (
          <StepConfirmation
            order={order}
            selectedItems={selectedItems}
            method={returnMethod}
            reasons={returnReasons}
            exchanges={exchangeVariants}
            onBack={navigateBack}
            orderNumber={orderNumber}
            email={email}
            onNext={(result) => {
              setSubmissionResult(result);
              setCurrentStep(STEPS.SUCCESS);
            }}
          />
        );
      case STEPS.SUCCESS:
        return (
          <StepSuccess
            result={submissionResult}
            onRestart={handleRestart}
          />
        );
      default:
        return <div>Unknown Step</div>;
    }
  };

  const getDotClass = (stepNumber) => {
    const activeMapping = {
      [STEPS.VERIFICATION]: 1,
      [STEPS.METHOD]: 2,
      [STEPS.PRODUCTS]: 3,
      [STEPS.REASON]: 4,
      [STEPS.EXCHANGE]: 5,
      [STEPS.CONFIRMATION]: returnMethod === "exchange" ? 6 : 5,
      [STEPS.SUCCESS]: returnMethod === "exchange" ? 7 : 6
    };

    const currentVisualStep = activeMapping[currentStep];
    const itemVisualStep = activeMapping[stepNumber];

    if (currentVisualStep === itemVisualStep) return "step-dot active";
    if (currentVisualStep > itemVisualStep) return "step-dot completed";
    return "step-dot";
  };

  return (
    <div className="portal-container">
      {currentStep !== STEPS.SUCCESS && (
        <div className="tab-container">
          <button
            className={`tab-btn ${activeTab === "portal" ? "active" : ""}`}
            onClick={() => setActiveTab("portal")}
            style={{ display: "flex", alignItems: "center", justifyContent: "center" }}
          >
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: "8px" }}>
              <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2" />
              <rect x="8" y="2" width="8" height="4" rx="1" ry="1" />
            </svg>
            Return Portal Form
          </button>
          <button
            className={`tab-btn ${activeTab === "agent" ? "active" : ""}`}
            onClick={() => setActiveTab("agent")}
            style={{ display: "flex", alignItems: "center", justifyContent: "center" }}
          >
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: "8px" }}>
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            </svg>
            AI Return Assistant
          </button>
        </div>
      )}

      {activeTab === "portal" || currentStep === STEPS.SUCCESS ? (
        <>
          {currentStep !== STEPS.SUCCESS && (
            <div className="step-indicator">
              <div className={getDotClass(STEPS.VERIFICATION)}>1</div>
              <div className={getDotClass(STEPS.METHOD)}>2</div>
              <div className={getDotClass(STEPS.PRODUCTS)}>3</div>
              <div className={getDotClass(STEPS.REASON)}>4</div>
              {returnMethod === "exchange" && (
                <div className={getDotClass(STEPS.EXCHANGE)}>5</div>
              )}
              <div className={getDotClass(STEPS.CONFIRMATION)}>
                {returnMethod === "exchange" ? "6" : "5"}
              </div>
            </div>
          )}
          {renderStep()}
        </>
      ) : (
        <ChatAgent />
      )}
    </div>
  );
}

export default App;
