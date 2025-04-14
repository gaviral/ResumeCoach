// ResumeCoach/frontend/src/App.tsx
import { useState, useEffect, useCallback, useRef } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import './App.css';

// --- Interfaces ---
interface ApiError {
    message: string;
    status?: number;
}

interface AnalysisResult {
    analysis: string;
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

function App() {
  // --- State Variables ---
  const [resumeText, setResumeText] = useState<string>(() => localStorage.getItem(LOCAL_STORAGE_RESUME_KEY) || '');
  const [jobDescriptionText, setJobDescriptionText] = useState<string>(() => localStorage.getItem(LOCAL_STORAGE_JD_KEY) || '');
  const [analysisResult, setAnalysisResult] = useState<string | null>(null);
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState<string>('');
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

  // Fetch default items on mount
  useEffect(() => {
    fetchDefaultItems();
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
      if (!apiUrl) {
          setError({ message: "API URL is not configured." });
          return;
      }
      setIsLoadingDefaults(true);
      clearStatus();
      console.log(`Fetching default items from: ${apiUrl}/items`);
      try {
          const response = await axios.get<DefaultItem[]>(`${apiUrl}/items`);
          setDefaultItems(response.data || []);
          setStatusMessage('Default examples list loaded.');
      } catch (err) {
          const formattedError = formatError(err);
          console.error("Error fetching default items:", err);
          setError({ message: `Failed to fetch default items: ${formattedError.message}`, status: formattedError.status });
          setDefaultItems([]); // Clear defaults on error
      } finally {
          setIsLoadingDefaults(false);
      }
  }, [apiUrl]);

  const loadDefaultContent = async (id: string, type: 'resume' | 'job_description') => {
      if (!apiUrl) { setError({ message: "API URL not configured." }); return; }
      setIsLoadingDefaults(true); // Reuse loading state
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
      setAnalysisResult(null); // Clear previous analysis
      setChatHistory([]); // Clear previous chat
      console.log(`Sending analysis request to: ${apiUrl}/analyze`);

      try {
          const response = await axios.post<AnalysisResult>(`${apiUrl}/analyze`, {
              resume: resumeText,
              job_description: jobDescriptionText,
          });
          setAnalysisResult(response.data.analysis);
          setStatusMessage("Analysis complete.");
      } catch (err) {
          const formattedError = formatError(err);
          console.error("Error during analysis:", err);
          let specificError = { message: `Analysis failed: ${formattedError.message}`, status: formattedError.status };
          if (formattedError.status === 503 || formattedError.message.toLowerCase().includes('api key')) {
              specificError.message = `Analysis failed: ${formattedError.message}. Please ensure the backend OpenAI API Key is configured correctly.`;
          }
          setError(specificError);
      } finally {
          setIsLoadingAnalysis(false);
      }
  };

  const handleChatSubmit = async () => {
      if (!apiUrl) { setError({ message: "API URL not configured." }); return; }
      if (!chatInput.trim()) { return; }
      if (!analysisResult) { setError({ message: "Please run an analysis before starting chat." }); return; }

      const newUserMessage: ChatMessage = { sender: 'user', text: chatInput };
      const historyToSend = [...chatHistory];

      // Update state *before* API call for immediate UI update
      setChatHistory(prev => [...prev, newUserMessage]);
      setChatInput('');
      setIsLoadingChat(true);
      clearStatus();
      console.log(`Sending chat request to: ${apiUrl}/chat`);

      try {
          const response = await axios.post<{ answer: string }>(`${apiUrl}/chat`, {
              resume: resumeText,
              job_description: jobDescriptionText,
              analysis_context: analysisResult,
              question: newUserMessage.text, // The current question
              chat_history: historyToSend,
          });

          const aiResponse: ChatMessage = { sender: 'ai', text: response.data.answer };
          // Add AI response, which will trigger the scroll effect again
          setChatHistory(prev => [...prev, aiResponse]);

      } catch (err) {
          const formattedError = formatError(err);
          console.error("Error during chat:", err);
          const errorText = `Sorry, I encountered an error: ${formattedError.message}`;
          const errorResponse: ChatMessage = { sender: 'ai', text: errorText };
          // Add error response, triggering scroll effect
          setChatHistory(prev => [...prev, errorResponse]);

          let specificError = { message: `Chat failed: ${formattedError.message}`, status: formattedError.status };
           if (formattedError.status === 503 || formattedError.message.toLowerCase().includes('api key')) {
              specificError.message = `Chat failed: ${formattedError.message}. Please ensure the backend OpenAI API Key is configured correctly.`;
          }
          setError(specificError);
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
      !error && statusMessage ? "success" : "",
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
                          disabled={isLoading}
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
                          disabled={isLoading}
                          rows={15}
                      />
                  </div>
              </div>
              <button
                  onClick={handleAnalyze}
                  disabled={isLoading || !apiUrl || !resumeText.trim() || !jobDescriptionText.trim()}
                  className="analyze-button"
              >
                  {isLoadingAnalysis ? 'Analyzing...' : 'Analyze Resume vs Job Description'}
              </button>
          </div>

          {/* --- Analysis Results --- */}
          {analysisResult && (
              <div className="card analysis-results">
                  <h2>Analysis Results</h2>
                  <div className="analysis-content">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {analysisResult}
                      </ReactMarkdown>
                  </div>
                  <div ref={analysisEndRef} /> {/* Keep analysisEndRef for scrolling analysis */}
              </div>
          )}

          {/* --- Chat Interface --- */}
          {analysisResult && (
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
                          disabled={isLoadingChat || !apiUrl}
                      />
                      <button type="submit" disabled={isLoadingChat || !apiUrl || !chatInput.trim()}>
                          Send
                      </button>
                  </form>
              </div>
          )}
      </div>
  );
}

export default App;