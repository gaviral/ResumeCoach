// ResumeCoach/frontend/src/App.tsx
import { useState, useEffect, useCallback } from 'react';
import axios from 'axios'; // Import AxiosError type
import './App.css'; // Basic styling

// Define the structure of an item (matching backend)
interface Item {
  id: string;
  content: string;
  createdAt: string;
  updatedAt: string;
}

// Define a type for API errors for better handling
interface ApiError {
    message: string;
    status?: number;
}

function App() {
  const [items, setItems] = useState<Item[]>([]);
  const [newItemContent, setNewItemContent] = useState<string>('');
  const [updateItemId, setUpdateItemId] = useState<string>('');
  const [updateItemContent, setUpdateItemContent] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<ApiError | null>(null); // Use ApiError type
  const [statusMessage, setStatusMessage] = useState<string>('');

  // Get API URL from environment variables (set by Vite during build)
  const apiUrl = import.meta.env.VITE_API_URL;

  // --- Helper to format errors ---
  const formatError = (err: unknown): ApiError => {
      if (axios.isAxiosError(err)) {
          const serverError = err.response?.data?.error; // Check for error message from backend
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

  // --- API Call Functions ---

  const fetchItems = useCallback(async () => {
    if (!apiUrl) {
      setError({ message: "API URL is not configured. Please set VITE_API_URL in your .env file and rebuild/redeploy." });
      return;
    }
    setLoading(true);
    setError(null);
    // Clear status message when starting fetch
    // setStatusMessage('');
    console.log(`Fetching items from: ${apiUrl}/items`);
    try {
      // Ensure the expected response type matches the backend
      const response = await axios.get<Item[]>(`${apiUrl}/items`);
      // Sort items by creation date (newest first) for better display
      const sortedItems = response.data.sort((a, b) =>
          new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
      );
      setItems(sortedItems);
      // Set status only on successful fetch, cleared otherwise
      setStatusMessage('Items fetched successfully.');
    } catch (err) {
      const formattedError = formatError(err);
      console.error("Error fetching items:", err);
      setError({ message: `Failed to fetch items: ${formattedError.message}`, status: formattedError.status });
      setStatusMessage(''); // Clear status on error
    } finally {
      setLoading(false);
    }
  }, [apiUrl]); // Dependency: only apiUrl

  const createItem = async () => {
    if (!apiUrl) { setError({ message: "API URL not configured." }); return; }
    if (!newItemContent.trim()) { setError({ message: "New item content cannot be empty." }); return; }

    setLoading(true);
    setError(null);
    setStatusMessage('');
    console.log(`Creating item at: ${apiUrl}/items with content: "${newItemContent}"`);
    try {
      // Send content in the request body as expected by the backend
      const response = await axios.post<Item>(`${apiUrl}/items`, { content: newItemContent });
      setNewItemContent(''); // Clear input field after successful creation
      setStatusMessage(`Item "${response.data.content}" created (ID: ${response.data.id}). Refreshing list...`);
      await fetchItems(); // Refetch the list to show the new item
    } catch (err) {
      const formattedError = formatError(err);
      console.error("Error creating item:", err);
      setError({ message: `Failed to create item: ${formattedError.message}`, status: formattedError.status });
      setStatusMessage(''); // Clear status on error
    } finally {
      setLoading(false);
    }
  };

  const updateItem = async () => {
    if (!apiUrl) { setError({ message: "API URL not configured." }); return; }
    if (!updateItemId.trim() || !updateItemContent.trim()) {
        setError({ message: "Both Item ID and New Content are required for update." });
        return;
    }

    setLoading(true);
    setError(null);
    setStatusMessage('');
    const itemToUpdateId = updateItemId; // Capture id before clearing fields
    const itemToUpdateContent = updateItemContent;
    console.log(`Updating item ID ${itemToUpdateId} at: ${apiUrl}/items/${itemToUpdateId} with content: "${itemToUpdateContent}"`);
    try {
      // Send new content in the request body
      await axios.put(`${apiUrl}/items/${itemToUpdateId}`, { content: itemToUpdateContent });
      setUpdateItemId(''); // Clear fields after successful update
      setUpdateItemContent('');
      setStatusMessage(`Item ID ${itemToUpdateId} updated. Refreshing list...`);
      await fetchItems(); // Refetch items to show the update
    } catch (err) {
       const formattedError = formatError(err);
       console.error("Error updating item:", err);
       // Provide specific feedback for 404
       if (formattedError.status === 404) {
           setError({ message: `Failed to update: Item with ID ${itemToUpdateId} not found.`, status: 404 });
       } else {
           setError({ message: `Failed to update item: ${formattedError.message}`, status: formattedError.status });
       }
       setStatusMessage(''); // Clear status on error
    } finally {
      setLoading(false);
    }
  };

  const deleteItem = async (id: string) => {
    if (!apiUrl) { setError({ message: "API URL not configured." }); return; }
    // Confirmation dialog
    if (!window.confirm(`Are you sure you want to permanently delete item ID ${id}?`)) {
        return;
    }

    setLoading(true);
    setError(null);
    setStatusMessage('');
    console.log(`Deleting item ID ${id} at: ${apiUrl}/items/${id}`);
    try {
      await axios.delete(`${apiUrl}/items/${id}`);
      setStatusMessage(`Item ID ${id} deleted. Refreshing list...`);
      await fetchItems(); // Refetch list to reflect deletion
    } catch (err) {
      const formattedError = formatError(err);
      console.error("Error deleting item:", err);
      setError({ message: `Failed to delete item: ${formattedError.message}`, status: formattedError.status });
      setStatusMessage(''); // Clear status on error
    } finally {
      setLoading(false);
    }
  };

  // --- Effects ---

  // Fetch items on initial component mount or when apiUrl changes
  useEffect(() => {
    if (apiUrl) {
        console.log("API URL is set. Fetching initial items.");
        fetchItems();
    } else {
        console.warn("API URL not available on mount.");
        // Display warning persistently if URL is missing
        setError({ message: "API URL is not configured. Please set VITE_API_URL in your .env file, then build and deploy." });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiUrl]); // fetchItems is memoized with useCallback, including it is optional but safe

  // --- Render ---

  return (
    <div className="App">
      <h1>ResumeCoach Foundation - CRUD Demo</h1>

      {/* Status Messages */}
      {loading && <p className="status loading"><i>Loading...</i></p>}
      {/* Display error prominently */}
      {error && <p className="status error"><b>Error:</b> {error.message} {error.status ? `(Status: ${error.status})` : ''}</p>}
      {/* Display status only if no error */}
      {statusMessage && !error && <p className="status success"><b>Status:</b> {statusMessage}</p>}
      {!apiUrl && <p className="status warning"><b>Warning:</b> VITE_API_URL is not set in .env</p>}

      {/* --- Create Item --- */}
      <div className="card">
        <h2>Create New Item</h2>
        <input
          type="text"
          aria-label="New item content"
          placeholder="Enter item content"
          value={newItemContent}
          onChange={(e) => setNewItemContent(e.target.value)}
          disabled={loading || !apiUrl}
        />
        <button onClick={createItem} disabled={loading || !apiUrl || !newItemContent.trim()}>
          Create Item
        </button>
      </div>

      {/* --- Update Item --- */}
      <div className="card">
        <h2>Update Item</h2>
        <input
          type="text"
          aria-label="Item ID to Update"
          placeholder="Item ID to Update"
          value={updateItemId}
          onChange={(e) => setUpdateItemId(e.target.value)}
          disabled={loading || !apiUrl}
        />
        <input
          type="text"
          aria-label="New Content for Update"
          placeholder="New Content"
          value={updateItemContent}
          onChange={(e) => setUpdateItemContent(e.target.value)}
          disabled={loading || !apiUrl}
        />
        <button onClick={updateItem} disabled={loading || !apiUrl || !updateItemId.trim() || !updateItemContent.trim()}>
          Update Item
        </button>
         <button onClick={() => { setUpdateItemId(''); setUpdateItemContent(''); setError(null); }} disabled={loading} className="secondary">
                Clear Update Fields
         </button>
      </div>

      {/* --- Read/List Items --- */}
      <div className="card">
        <h2>Items List</h2>
        <button onClick={fetchItems} disabled={loading || !apiUrl}>
          Refresh List
        </button>
        {items.length === 0 && !loading && apiUrl && <p>No items found in the database.</p>}
        <ul>
          {items.map((item) => (
            <li key={item.id}>
              <div><strong>ID:</strong> {item.id}</div>
              <div><strong>Content:</strong> {item.content}</div>
              <div><strong>Created:</strong> {new Date(item.createdAt).toLocaleString()}</div>
              <div><strong>Updated:</strong> {new Date(item.updatedAt).toLocaleString()}</div>
              <div className="item-actions">
                  <button
                      onClick={() => { setUpdateItemId(item.id); setUpdateItemContent(item.content); window.scrollTo(0, 0); setError(null); setStatusMessage(''); }}
                      disabled={loading || !apiUrl}
                      className="edit"
                      aria-label={`Edit item ${item.id}`}
                   >
                    Edit
                  </button>
                  <button
                      onClick={() => deleteItem(item.id)}
                      disabled={loading || !apiUrl}
                      className="delete"
                      aria-label={`Delete item ${item.id}`}
                   >
                    Delete
                  </button>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

export default App;