// ResumeCoach/frontend/src/App.tsx
import { useState, useEffect, useCallback, useRef } from 'react';
import axios, { AxiosResponse } from 'axios'; // Import AxiosResponse
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import './App.css';

// --- Interfaces ---
interface ApiError {
    message: string;
    status?: number;
}

// Updated AnalysisResult interface to expect sessionId
interface AnalysisResult {
    analysis: string;
    sessionId: string; // Expect sessionId from /analyze response body
}

interface ChatMessage {
    sender: 'user' | 'ai';
    text: string;
}

interface DefaultItem {
    id: string;
    name: string;
}

interface DefaultItemContent {
    id: string;
    content: string;
}

// --- Constants ---
const LOCAL_STORAGE_RESUME_KEY = 'resumeCoach_resumeText';
const LOCAL_STORAGE_JD_KEY = 'resumeCoach_jobDescriptionText';
// Use sessionStorage for sessionId - it clears when the tab/browser closes
const SESSION_STORAGE_SESSION_ID_KEY = 'resumeCoach_sessionId';


function App() {
  // --- State Variables ---
  const [resumeText, setResumeText] = useState<string>(() => localStorage.getItem(LOCAL_STORAGE_RESUME_KEY) || '');
  const [jobDescriptionText, setJobDescriptionText] = useState<string>(() => localStorage.getItem(LOCAL_STORAGE_JD_KEY) || '');
  const [analysisResult, setAnalysisResult] = useState<string | null>(null);
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState<string>('');
  // Add state for session ID, initialize from sessionStorage
  const [sessionId, setSessionId] = useState<string | null>(() => sessionStorage.getItem(SESSION_STORAGE_SESSION_ID_KEY));
  const [isLoadingAnalysis, setIsLoadingAnalysis] = useState<boolean>(false);
  const [isLoadingChat, setIsLoadingChat] = useState<boolean>(false);
  const [isLoadingDefaults, setIsLoadingDefaults] = useState<boolean>(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [statusMessage, setStatusMessage] = useState<string>('');
  const [defaultItems, setDefaultItems] = useState<DefaultItem[]>([]);

  // Refs for scrolling
  const analysisEndRef = useRef<null | HTMLDivElement>(null);
  const chatHistoryRef = useRef<null | HTMLDivElement>(null);

  // Get API URL from environment variables
  const apiUrl = import.meta.env.VITE_API_URL;

  // --- Effects ---

  // Save text to local storage on change
  useEffect(() => {
    localStorage.setItem(LOCAL_STORAGE_RESUME_KEY, resumeText);
  }, [resumeText]);

  useEffect(() => {
    localStorage.setItem(LOCAL_STORAGE_JD_KEY, jobDescriptionText);
  }, [jobDescriptionText]);

  // Scroll analysis into view when content updates
  useEffect(() => {
    analysisEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [analysisResult]);

  // Scroll chat history container to bottom when chatHistory changes
  useEffect(() => {
    if (chatHistoryRef.current) {
      chatHistoryRef.current.scrollTop = chatHistoryRef.current.scrollHeight;
    }
  }, [chatHistory]);

  // Effect to save session ID to sessionStorage
  useEffect(() => {
    if (sessionId) {
      sessionStorage.setItem(SESSION_STORAGE_SESSION_ID_KEY, sessionId);
      console.log("Session ID saved:", sessionId);
    } else {
      sessionStorage.removeItem(SESSION_STORAGE_SESSION_ID_KEY);
      console.log("Session ID removed from storage.");
    }
  }, [sessionId]);


  // Fetch default items on mount
  useEffect(() => {
    fetchDefaultItems();
    // Check if session ID exists on load, maybe show a message?
    if (sessionId) {
        setStatusMessage(`Existing session detected: ${sessionId}. You can continue chatting or start a new analysis.`);
        // We don't automatically load the analysis/history here,
        // user needs to interact or start new analysis.
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiUrl]); // Dependency: apiUrl

  // --- Helper Functions ---
  const formatError = (err: unknown): ApiError => {
      if (axios.isAxiosError(err)) {
          const serverError = err.response?.data?.error;
          return {
              message: serverError || err.message || 'An Axios error occurred',
              status: err.response?.status
          };
      } else if (err instanceof Error) {
          return { message: err.message };
      } else {
          return { message: 'An unknown error occurred' };
      }
  };

  const clearStatus = () => {
      setError(null);
      setStatusMessage('');
  };

  // --- API Call Functions ---

  const fetchDefaultItems = useCallback(async () => {
      if (!apiUrl) { setError({ message: "API URL is not configured." }); return; }
      setIsLoadingDefaults(true);
      clearStatus();
      console.log(`Fetching default items from: ${apiUrl}/items`);
      try {
          const response = await axios.get<DefaultItem[]>(`${apiUrl}/items`);
          setDefaultItems(response.data || []);
          // Don't overwrite session status message here
          // setStatusMessage('Default examples list loaded.');
      } catch (err) {
          const formattedError = formatError(err);
          console.error("Error fetching default items:", err);
          setError({ message: `Failed to fetch default items: ${formattedError.message}`, status: formattedError.status });
          setDefaultItems([]);
      } finally {
          setIsLoadingDefaults(false);
      }
  }, [apiUrl]);

  const loadDefaultContent = async (id: string, type: 'resume' | 'job_description') => {
      if (!apiUrl) { setError({ message: "API URL not configured." }); return; }
      setIsLoadingDefaults(true);
      clearStatus();
      console.log(`Loading content for default item ID: ${id}`);
      try {
          const response = await axios.get<DefaultItemContent>(`${apiUrl}/items/${id}`);
          if (response.data && response.data.content) {
              if (type === 'resume') {
                  setResumeText(response.data.content);
              } else {
                  setJobDescriptionText(response.data.content);
              }
              setStatusMessage(`Loaded content for ${id}.`);
          } else {
               throw new Error("Content not found in response.");
          }
      } catch (err) {
          const formattedError = formatError(err);
          console.error(`Error loading default content for ${id}:`, err);
          setError({ message: `Failed to load content for ${id}: ${formattedError.message}`, status: formattedError.status });
      } finally {
          setIsLoadingDefaults(false);
      }
  };


  const handleAnalyze = async () => {
      if (!apiUrl) { setError({ message: "API URL not configured." }); return; }
      if (!resumeText.trim() || !jobDescriptionText.trim()) {
          setError({ message: "Please provide both resume and job description text." });
          return;
      }

      setIsLoadingAnalysis(true);
      clearStatus();
      setAnalysisResult(null);
      setChatHistory([]);
      // Clear previous session ID on new analysis
      setSessionId(null);
      console.log(`Sending analysis request to: ${apiUrl}/analyze`);

      try {
          // Expect AnalysisResult type (includes sessionId)
          const response: AxiosResponse<AnalysisResult> = await axios.post(`${apiUrl}/analyze`, {
              resume: resumeText,
              job_description: jobDescriptionText,
          });

          setAnalysisResult(response.data.analysis);
          // Store the new session ID from response body
          setSessionId(response.data.sessionId);
          setStatusMessage(`Analysis complete. Session started: ${response.data.sessionId}`);
          console.log("Received session ID:", response.data.sessionId);

      } catch (err) {
          const formattedError = formatError(err);
          console.error("Error during analysis:", err);
          const specificError = { message: `Analysis failed: ${formattedError.message}`, status: formattedError.status };
          if (formattedError.status === 503 || formattedError.message.toLowerCase().includes('api key')) {
              specificError.message = `Analysis failed: ${formattedError.message}. Please ensure the backend OpenAI API Key is configured correctly.`;
          }
          setError(specificError);
          setSessionId(null); // Clear session on analysis error
      } finally {
          setIsLoadingAnalysis(false);
      }
  };

  const handleChatSubmit = async () => {
      if (!apiUrl) { setError({ message: "API URL is not configured." }); return; }
      if (!chatInput.trim()) { return; }
      // Check for sessionId AND analysisResult (analysisResult implies a session should exist)
      if (!analysisResult || !sessionId) {
          setError({ message: "Please run an analysis to start or continue a chat session." });
          return;
      }

      const newUserMessage: ChatMessage = { sender: 'user', text: chatInput };

      // Update UI immediately
      setChatHistory(prev => [...prev, newUserMessage]);
      setChatInput('');
      setIsLoadingChat(true);
      clearStatus();
      console.log(`Sending chat request to: ${apiUrl}/chat for session: ${sessionId}`);

      try {
           // Send only question and sessionId
          const response = await axios.post<{ answer: string }>(`${apiUrl}/chat`, {
              question: newUserMessage.text,
              sessionId: sessionId, // Send the current session ID
          });

          const aiResponse: ChatMessage = { sender: 'ai', text: response.data.answer };
          setChatHistory(prev => [...prev, aiResponse]);

      } catch (err) {
          const formattedError = formatError(err);
          console.error("Error during chat:", err);
          let errorText = `Sorry, I encountered an error: ${formattedError.message}`;
          // Check if session expired (404 error from backend)
          if (formattedError.status === 404) {
              errorText = "Your session may have expired or was not found. Please start a new analysis.";
              setSessionId(null); // Clear expired/invalid session ID
              setAnalysisResult(null); // Clear analysis to hide chat interface
              setChatHistory([]); // Clear chat history display
          }
          const errorResponse: ChatMessage = { sender: 'ai', text: errorText };
          setChatHistory(prev => [...prev, errorResponse]); // Show error in chat

          const specificError = { message: `Chat failed: ${formattedError.message}`, status: formattedError.status };
           if (formattedError.status === 503 || formattedError.message.toLowerCase().includes('api key')) {
              specificError.message = `Chat failed: ${formattedError.message}. Please ensure the backend OpenAI API Key is configured correctly.`;
          }
          setError(specificError); // Also show error in status bar
      } finally {
          setIsLoadingChat(false);
      }
  };

  // Determine status container classes
  const isLoading = isLoadingAnalysis || isLoadingChat || isLoadingDefaults;
  const showStatusContainer = isLoading || error || statusMessage || !apiUrl;
  const statusContainerClasses = [
      "status-container",
      showStatusContainer ? "visible" : "",
      isLoading ? "loading" : "",
      error ? "error" : "",
      !error && statusMessage ? "success" : "", // Show session status as success for now
      !apiUrl ? "warning" : ""
  ].filter(Boolean).join(" ");

  // --- Render ---
  return (
      <div className="App">
          <h1>Resume Coach</h1>

          {/* --- Status/Error Display --- */}
          <div className={statusContainerClasses}>
              { isLoading && <p className="status"><i>Loading... Please wait.</i></p> }
              { error && <p className="status"><b>Error:</b> {error.message} {error.status ? `(Status: ${error.status})` : ''}</p> }
              { !error && statusMessage && <p className="status"><b>Status:</b> {statusMessage}</p> }
              { !apiUrl && <p className="status"><b>Configuration Warning:</b> VITE_API_URL is not set. API calls will fail.</p> }
          </div>

          {/* --- Default Loaders --- */}
          <div className="card defaults-loader">
              <h2>Load Examples</h2>
              <div className="default-buttons">
                  {defaultItems.filter(item => item.id.includes('RESUME')).map(item => (
                      <button key={item.id} onClick={() => loadDefaultContent(item.id, 'resume')} disabled={isLoading || !apiUrl}>
                          Load: {item.name} (Resume)
                      </button>
                  ))}
                  {defaultItems.filter(item => item.id.includes('JOB_DESC')).map(item => (
                      <button key={item.id} onClick={() => loadDefaultContent(item.id, 'job_description')} disabled={isLoading || !apiUrl}>
                          Load: {item.name} (JD)
                      </button>
                  ))}
              </div>
               <button onClick={fetchDefaultItems} disabled={isLoadingDefaults || !apiUrl} className="secondary">
                   Refresh Examples List
               </button>
          </div>


          {/* --- Inputs --- */}
          <div className="card input-area">
              <h2>Inputs</h2>
              <div className="input-grid">
                  <div className="input-column">
                      <label htmlFor="resumeInput">Your Resume</label>
                      <textarea
                          id="resumeInput"
                          aria-label="Resume Text"
                          placeholder="Paste your full resume text here..."
                          value={resumeText}
                          onChange={(e) => setResumeText(e.target.value)}
                          disabled={isLoadingAnalysis} // Only disable during analysis
                          rows={15}
                      />
                  </div>
                  <div className="input-column">
                      <label htmlFor="jobDescriptionInput">Target Job Description</label>
                      <textarea
                          id="jobDescriptionInput"
                          aria-label="Job Description Text"
                          placeholder="Paste the target job description text here..."
                          value={jobDescriptionText}
                          onChange={(e) => setJobDescriptionText(e.target.value)}
                          disabled={isLoadingAnalysis} // Only disable during analysis
                          rows={15}
                      />
                  </div>
              </div>
              <button
                  onClick={handleAnalyze}
                  disabled={isLoadingAnalysis || !apiUrl || !resumeText.trim() || !jobDescriptionText.trim()}
                  className="analyze-button"
              >
                  {isLoadingAnalysis ? 'Analyzing...' : 'Analyze Resume & Start Session'}
              </button>
          </div>

          {/* --- Analysis Results --- */}
          {/* Show analysis result if it exists (even if session expired, show last known analysis) */}
          {analysisResult && (
              <div className="card analysis-results">
                  <h2>Analysis Results</h2>
                   {/* Optionally show session ID */}
                   {sessionId && <p style={{fontSize: '0.8em', color: 'grey', marginTop: '-10px', marginBottom: '10px'}}>Session ID: {sessionId}</p>}
                  <div className="analysis-content">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {analysisResult}
                      </ReactMarkdown>
                  </div>
                  <div ref={analysisEndRef} />
              </div>
          )}

          {/* --- Chat Interface --- */}
          {/* Show chat interface only if analysisResult AND sessionId exist */}
          {analysisResult && sessionId && (
              <div className="card chat-interface">
                  <h2>Follow-up Chat</h2>
                  <div className="chat-history" ref={chatHistoryRef}>
                      {chatHistory.map((msg, index) => (
                          <div key={index} className={`chat-message ${msg.sender}`}>
                              <span className="sender-label">{msg.sender === 'user' ? 'You' : 'AI Coach'}:</span>
                              <div className="message-text">
                                <ReactMarkdown remarkPlugins={[remarkGfm]} components={{ p: 'span' }}>
                                    {msg.text}
                                </ReactMarkdown>
                              </div>
                          </div>
                      ))}
                      {isLoadingChat && <div className="chat-message ai loading"><i>AI Coach is thinking...</i></div>}
                  </div>
                  <form className="chat-input-area" onSubmit={(e) => { e.preventDefault(); handleChatSubmit(); }}>
                      <input
                          type="text"
                          aria-label="Chat input"
                          placeholder="Ask a follow-up question (e.g., 'Suggest improvements for...') "
                          value={chatInput}
                          onChange={(e) => setChatInput(e.target.value)}
                          disabled={isLoadingChat || !apiUrl || !sessionId} // Disable if no session
                      />
                      <button type="submit" disabled={isLoadingChat || !apiUrl || !chatInput.trim() || !sessionId}>
                          Send
                      </button>
                  </form>
              </div>
          )}
      </div>
  );
}

export default App;