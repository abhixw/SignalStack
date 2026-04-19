import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { User, ArrowRight } from 'lucide-react';

export default function CandidatePortal() {
    const [candidateId, setCandidateId] = useState('');
    const navigate = useNavigate();

    const handleLogin = (e) => {
        e.preventDefault();
        if (candidateId.trim()) {
            localStorage.setItem('candidateId', candidateId);
            navigate('/candidate/jobs');
        }
    };

    return (
        <div className="min-h-full flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
            <div className="max-w-md w-full space-y-8 bg-white p-10 rounded-xl shadow-lg border border-gray-100">
                <div>
                    <div className="mx-auto h-12 w-12 rounded-full bg-indigo-100 flex items-center justify-center">
                        <User className="h-6 w-6 text-indigo-600" />
                    </div>
                    <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
                        Candidate Portal
                    </h2>
                    <p className="mt-2 text-center text-sm text-gray-600">
                        Enter your ID or Email to see job postings and your application status.
                    </p>
                </div>
                <form className="mt-8 space-y-6" onSubmit={handleLogin}>
                    <div className="rounded-md shadow-sm -space-y-px">
                        <div>
                            <label htmlFor="candidate-id" className="sr-only">Candidate ID</label>
                            <input
                                id="candidate-id"
                                name="id"
                                type="text"
                                required
                                value={candidateId}
                                onChange={(e) => setCandidateId(e.target.value)}
                                className="appearance-none rounded-none relative block w-full px-3 py-3 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm"
                                placeholder="Enter your ID (e.g. name@example.com)"
                            />
                        </div>
                    </div>

                    <div>
                        <button
                            type="submit"
                            className="group relative w-full flex justify-center py-3 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors"
                        >
                            <span className="absolute left-0 inset-y-0 flex items-center pl-3">
                                <ArrowRight className="h-5 w-5 text-indigo-500 group-hover:text-indigo-400" aria-hidden="true" />
                            </span>
                            Enter Portal
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
